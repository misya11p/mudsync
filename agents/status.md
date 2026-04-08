## Project overview
- `mudsync` は GPU サーバー連携用の Python CLI。
- 主要コマンドは `config`, `show`, `connect`, `manage`, `sync`, `run`, `jupyter`。
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
  1. `run` を compose yaml 前提へ戻し、`gpus` などの追加は取り下げ
  2. `run` に `--no-rm` を追加（指定時は `--rm` を付けない）
  3. `run` に `-d` / `--detach` を追加
  4. `run` に `--name` を追加
- 完了済み:
  - `src/mudsync/cli.py`
    - `run` に `--no-rm`, `--detach/-d`, `--name` を追加
    - `run_cmd.command(...)` へ新オプションを受け渡し
  - `src/mudsync/commands/run.py`
    - `build_remote_run_command` と `build_remote_build_then_run_command` に
      `no_rm` / `detach` / `name` 適用ロジックを追加
    - `command()` に同オプションを追加し、生成コマンドへ反映
  - `tests/test_cli_and_run.py`
    - CLI引数パース（`--no-rm`, `--detach`, `--name`）の検証を追加
    - リモートコマンド生成で `--rm` の有無、`--detach` / `--name` 反映を検証
- 検証結果:
  - `uv run python -m unittest discover -s tests`
  - 22 tests passed
- 現在作業中:
  - なし
- 現在の課題:
  - なし
- 次のステップ:
  1. 追加要望待ち
