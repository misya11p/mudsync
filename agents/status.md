## Project overview
- `mudsync` は GPU サーバー連携用の Python CLI。
- 主要コマンドは `config`, `info`, `connect`, `manage`, `sync`, `run`, `jupyter`。
- 同期機能は rsync ベースで、`sync` は project 全体同期（local -> remote）として運用。

## Code explanations
- CLI エントリ: `src/mudsync/cli.py`
- 同期系:
  - `src/mudsync/commands/sync.py`: project 全体同期（exclude-from 方式）
  - `src/mudsync/commands/manage.py`: `sync` 向け除外ルールの管理
  - `src/mudsync/sync_rules.py`: プロジェクト別除外ルールの保存/読込
- 実行系:
  - `src/mudsync/commands/run.py`: `docker compose run --rm` 実行
  - `src/mudsync/commands/jupyter.py`: `docker compose up` + URL 検出 + Ctrl+C 時 `down`

## Current status
- 種別: plan 更新
- 受領指示:
  1. 実装対象を `agents/` に詳細化する
  2. 既存 `agents/plans` の完了済み計画を削除する
  3. 新要件として `sync` 維持、`push`/`pull`（個別転送）追加方針を反映する
- 完了済み:
  - 旧計画ファイルを削除:
    - `agents/plans/plan.md`
    - `agents/plans/spec.md`
    - `agents/plans/tasks/01_cli_surface_cleanup.md`
    - `agents/plans/tasks/02_run_compose_migration.md`
    - `agents/plans/tasks/03_jupyter_refactor.md`
    - `agents/plans/tasks/04_tests_and_regression.md`
  - 新計画を作成:
    - `agents/plans/plan.md`
    - `agents/plans/spec.md`
    - `agents/plans/tasks/01_cli_add_push_pull.md`
    - `agents/plans/tasks/02_rsync_common_refactor.md`
    - `agents/plans/tasks/03_push_pull_filtered_transfer.md`
    - `agents/plans/tasks/04_tests_and_regression_for_transfer.md`
- 現在作業中:
  - 実装は未着手（計画定義のみ完了）
- 現在の課題:
  - `push` / `pull` の CLI 文言とエラーメッセージの最終トーン調整が未確定
- 次のステップ:
  1. Task 01 から順に実装開始
  2. push/pull の rsync include ルール順序テストを先に追加
