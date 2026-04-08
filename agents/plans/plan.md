## MUDSync 実装計画（sync 維持 + push/pull 追加）

### 背景
- 現行の `sync` はプロジェクト全体の local -> remote 同期として運用されている。
- 新要件として、個別転送用途を `push`（local -> remote）と `pull`（remote -> local）として分離したい。
- モデル成果物の取得など、限定的なファイル回収を安全に行うため、`pull` は glob pattern による明示指定を前提とする。

### ゴール
1. `sync` は既存仕様を維持する（挙動変更なし）。
2. `push` コマンドを追加し、glob pattern ベースの個別転送を提供する。
3. `pull` コマンドを追加し、glob pattern ベースの逆方向個別転送を提供する。
4. 個別転送は include ベースで実装し、巨大な exclude 管理を不要にする。
5. 実装詳細をテストで担保し、既存 `run` / `jupyter` への影響を防ぐ。

### スコープ
- CLI 追加: `push`, `pull`
- 既存 `sync` の保持
- rsync 実行ロジックの共通化（内部実装再利用）
- push/pull のパターン処理（include ルール生成）
- 単体テスト追加

### 非スコープ
- `manage` の機能拡張（push/pull 用の別ルール管理は実施しない）
- `sync` の管理ルール形式変更
- SSH ポートフォワードや転送プロトコル追加（scp 併用など）

### 技術方針
- 転送は `rsync` で統一する（既存資産を活かし、差分転送と圧縮を利用）。
- `sync` は現行の exclude ベース処理をそのまま維持。
- `push` / `pull` は include ベース:
  - `--include='*/'`
  - `--include='<user pattern>'`（複数）
  - `--exclude='*'`
  - `--prune-empty-dirs`
- パターンは Typer の引数として受け取り、シェル展開回避のためユーザーにはクオートを推奨。

### 実装アーキテクチャ
- `src/mudsync/cli.py`
  - `push` / `pull` エントリ追加
  - `sync` エントリは維持
- `src/mudsync/commands/sync.py`
  - 既存 `sync` は維持
  - rsync コマンド組み立ての共通ヘルパーを追加し、`push` / `pull` から再利用
- `src/mudsync/commands/push.py`（新規）
  - pattern 引数の検証
  - include ルールで local -> remote 個別転送
- `src/mudsync/commands/pull.py`（新規）
  - pattern 引数の検証
  - include ルールで remote -> local 個別転送

### 検証戦略
- 単体テストでコマンド引数配列を検証（subprocess モック）。
- `sync` の既存挙動が変わっていないことを回帰確認。
- `push` / `pull` で include/exclude ルール順序が正しいことを検証。

### リスクと対策
- glob の解釈差異: ルール順序を固定し、テストで保証。
- 誤転送: `push` / `pull` は pattern 必須にして対象を限定。
- 既存機能への副作用: 共通化範囲を最小化し、`sync` は現行パスを維持。
