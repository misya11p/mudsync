## MUDSync 改良計画（run 統合 + docker compose 対応）

### 背景
- 現状は `build` / `run` / `jupyter` が `docker` ベースで分離されており、`build` の運用負荷とテスト不足が課題。
- 要求は `build` 廃止と `run` への統合、さらに単一 `Dockerfile` 前提から `docker compose` 前提への移行。

### ゴール
1. `build` コマンドを削除し、`run` で必要時にビルド可能にする。
2. `run` / `jupyter` の実行基盤を `docker compose` に統一する。
3. 現在未検証の `run` / `jupyter` を自動テストで担保する。

### スコープ
- CLI 引数仕様の整理（`run`: `--service`, `--build`, `--sync`, `--file`）
- リモート実行コマンド生成の compose 化
- `jupyter` の `run` 基盤への寄せ込み（重複処理削減）
- テスト追加（単体 + コマンド生成の検証）

### 非スコープ
- `config` / `show` / `connect` / `manage` / `sync` の挙動変更
- Docker イメージ設計や compose ファイルの中身そのものの最適化

### 技術方針
- `docker compose run --rm [--build] [--file] SERVICE COMMAND...` を基本形にする。
- 追加依存は原則なし。サービス解決は `docker compose config --services` の利用を第一候補とし、YAGNI で実装を小さく保つ。
- コマンド実行は既存同様 `subprocess.run` を維持し、既存設計との整合を優先。

### 実装アーキテクチャ
- `src/mudsync/cli.py`
  - `build` エントリ削除
  - `run` オプションの Typer 定義強化
- `src/mudsync/commands/run.py`
  - compose コマンド生成の中核
  - 必要なら事前 `sync` 呼び出し
  - デフォルトサービス解決ロジック
- `src/mudsync/commands/jupyter.py`
  - compose ベースに置換
  - `run` 共通ロジックを再利用

### 検証戦略
- コマンド生成の純粋関数化（可能な範囲）で単体テストしやすくする。
- `subprocess.run` をモックし、以下を検証:
  - `--build` 有無で引数が変わる
  - `--file` 指定時に compose ファイルが反映される
  - service 未指定時のデフォルト選択
  - jupyter の URL / port 表示ロジック

### リスクと対策
- `docker compose` バージョン差異: 対象オプションを最小限に限定し、失敗時エラーメッセージを明確化。
- service 自動選択の曖昧さ: 明示指定推奨のエラー文を用意。
- SSH 経由実行時の quoting 崩れ: `shlex.quote` で引数境界を保護。
