## Project overview
- `mudsync` は GPU サーバー連携用の Python CLI。
- 主要コマンドは `config`, `show`, `connect`, `manage`, `sync`, `run`, `jupyter`。
- リモート実行は SSH + Docker Compose を中心に利用する構成へ移行中。

## Code explanations
- CLI エントリ: `src/mudsync/cli.py`
- 実行系コマンド:
  - `src/mudsync/commands/run.py`: `docker compose run --rm` 実行
  - `src/mudsync/commands/jupyter.py`: `docker compose up` フォアグラウンド実行 + URL 検出 + Ctrl+C 時 `down`
  - `src/mudsync/commands/compose.py`: compose ファイル探索 / service 解決 / SSH コマンド組み立て共通処理
- 同期系:
  - `src/mudsync/commands/sync.py`: rsync 同期
  - `src/mudsync/commands/manage.py`: 同期ルール管理
- テスト:
  - `tests/test_cli_and_run.py`: `build` 廃止、`run` コマンド生成・終了コード伝播
  - `tests/test_jupyter.py`: URL ヘルパー、`up/down` コマンド生成、Ctrl+C 時 cleanup

## Current status
- 種別: instructions 実行中
- 受領指示: 「指示に従い、plan通りにcodingを完了しなさい」
- 完了済み:
  - `cli.py` から `build` サブコマンドを削除
  - `run` に `--service`, `--build`, `--sync`, `--file` を追加し、`COMMAND` 必須化
  - `compose.py` を新設し、compose ファイル探索 / service 自動解決 / SSH 実行共通化を実装
  - `run.py` を `docker compose run --rm` ベースへ移行
  - `jupyter.py` を `docker compose up` フォアグラウンド実行へ移行
  - `jupyter.py` でログから token URL を検出し、Host/Port 差し替え表示を追加
  - `jupyter.py` で Ctrl+C 時に `docker compose down` を実行する cleanup を追加
  - `tests/` を新設し、`run` / `jupyter` 回帰テストを追加
- 現在作業中:
  - テスト実行による回帰確認
- 現在の課題:
  - なし（現時点で既知のブロッカーなし）
- 次のステップ:
  1. `python -m unittest discover -s tests` を実行
  2. 失敗時は実装修正後に再実行
