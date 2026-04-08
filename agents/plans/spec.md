## 仕様（実装準備版）

### 1. CLI コマンド仕様

#### 1.1 `sync`
- 形式: `mudsync sync`
- 目的: プロジェクト全体の local -> remote 同期
- 挙動: 現行仕様を完全維持（内部挙動・オプション・表示文言を原則変更しない）

#### 1.2 `push`
- 形式: `mudsync push PATTERN [PATTERN ...]`
- 目的: local -> remote の個別転送
- 引数:
  - `PATTERN`（必須, 複数可）: プロジェクトルート基準の glob pattern
- 挙動:
  1. app config / project / ssh 情報を解決
  2. rsync include ルールを生成
  3. local project root を送信元、remote project path を送信先として実行

#### 1.3 `pull`
- 形式: `mudsync pull PATTERN [PATTERN ...]`
- 目的: remote -> local の個別転送
- 引数:
  - `PATTERN`（必須, 複数可）: プロジェクトルート基準の glob pattern
- 挙動:
  1. app config / project / ssh 情報を解決
  2. rsync include ルールを生成
  3. remote project path を送信元、local project root を送信先として実行

### 2. rsync 共通仕様

#### 2.1 使用方針
- `sync`, `push`, `pull` はすべて rsync を利用する。
- SSH オプション（port / identity_file / StrictHostKeyChecking）は既存実装と同等に扱う。

#### 2.2 push/pull の include ルール
- ルール順序は固定:
  1. `--include='*/'`
  2. 各 `PATTERN` を `--include='<pattern>'` として追加
  3. `--exclude='*'`
- `--prune-empty-dirs` を付与する。
- `--delete` は付与しない。

#### 2.3 sync の扱い
- `sync` は現状どおり `exclude-from` 方式を維持する。
- `manage` は `sync` の除外ルール管理として継続する。

### 3. エラーハンドリング
- PATTERN 未指定（push/pull）: Typer 引数エラー。
- rsync 未インストール: 既存と同様の案内メッセージ。
- rsync 実行失敗: 終了コード付きで失敗を返す。

### 4. 表示メッセージ
- `sync`: 既存表示を維持。
- `push`: `Syncing(local->remote, filtered)` の趣旨が伝わるメッセージを表示。
- `pull`: `Syncing(remote->local, filtered)` の趣旨が伝わるメッセージを表示。
- push/pull では適用 pattern 数を表示する。

### 5. manage の位置づけ
- `manage` は push/pull の設定対象にしない。
- ヘルプ文は必要なら「sync 用ルール管理」と分かる文言へ更新する。

### 6. テスト仕様
- `tests/test_cli_and_run.py`:
  - CLI に `push` / `pull` が公開されること
- 新規テスト（例: `tests/test_sync_push_pull.py`）:
  - push で include ルール順序が正しい
  - pull で include ルール順序が正しい
  - push/pull の source/destination が正しい
  - sync の既存コマンド生成が変化していない

### 7. 互換性
- 既存利用者の `mudsync sync` はそのまま有効。
- 新規用途として `mudsync push` / `mudsync pull` を追加。
