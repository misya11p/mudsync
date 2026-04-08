## Project overview
- `mudsync` は GPU サーバー連携用の Python CLI。
- 主要コマンドは `config`, `info`, `connect`, `manage`, `sync`, `run`, `jupyter`。
- リモート実行は SSH + Docker Compose を中心に利用する構成へ移行中。

## Code explanations
- CLI エントリ: `src/mudsync/cli.py`
- 実行系コマンド:
  - `src/mudsync/commands/run.py`: `docker compose run --rm` 実行
  - `src/mudsync/commands/jupyter.py`: `docker compose up` フォアグラウンド実行 + URL 検出 + Ctrl+C 時 `down`
  - `src/mudsync/commands/compose.py`: `--file` 明示時のみ検証 + service 解決 + SSH コマンド組み立て共通処理
- 同期系:
  - `src/mudsync/commands/sync.py`: rsync 同期
  - `src/mudsync/commands/manage.py`: 同期ルール管理
- テスト:
  - `tests/test_cli_and_run.py`: `build` 廃止、`run` コマンド生成・終了コード伝播
  - `tests/test_jupyter.py`: URL ヘルパー、`up/down` コマンド生成、Ctrl+C 時 cleanup

## Current status
- 種別: instructions 完了
- 受領指示:
  1. `show` コマンド名を `info` に変更
- 完了済み:
  - `src/mudsync/cli.py`
    - `show` サブコマンドを `info` にリネーム（内部実装は `show_cmd.command()` を再利用）
  - `agents/readme.md`
    - コマンド見出しを `show` から `info` に更新
  - `agents/status.md`
    - 主要コマンド一覧を `info` に更新
- 検証結果:
  - `uv run python -m unittest discover -s tests`
  - 25 tests passed（直近実行結果。今回変更はCLI表面名のみ）
- 現在作業中:
  - なし
- 現在の課題:
  - なし
- 次のステップ:
  1. 追加要望待ち
