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
  1. `config` で現在設定値をデフォルト値として表示
  2. `config` のサーバー選択順を文字列順で固定
  3. `config` と `manage` で終了導線を追加（会話中に Ctrl+C でも可）
- 完了済み:
  - `src/mudsync/commands/config.py`
    - サーバー一覧を `sorted()` で安定ソート
    - 既存設定を読み込み、`ssh_host` と `remote_home` をプロンプトのデフォルトに反映
    - `raise_keyboard_interrupt=False` により Ctrl+C 時は `Config cancelled.` で正常終了
    - `global_excludes` を再設定時にも保持
  - `src/mudsync/commands/manage.py`
    - 操作ヘルプに `esc/q/ctrl+c: cancel` を追加
    - `escape` / `q` キーで `cancelled` 終了できるよう追加
    - キャンセル時に `Sync rules update cancelled.` を表示
  - `tests/test_config.py` を追加
    - ソート済み選択肢、既存値デフォルト反映、`global_excludes` 保持を検証
    - キャンセル時に保存されないことを検証
- 検証結果:
  - `uv run python -m unittest discover -s tests`
  - 19 tests passed
- 現在作業中:
  - なし
- 現在の課題:
  - なし
- 次のステップ:
  1. 追加要望待ち
