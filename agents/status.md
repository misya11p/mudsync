## Project overview
- `mudsync` は GPU サーバー連携用の Python CLI。
- 現在の主要コマンドは `config`, `show`, `connect`, `manage`, `sync`, `build`, `run`, `jupyter`。
- リモート実行は SSH + Docker を利用している。

## Code explanations
- CLI エントリ: `src/mudsync/cli.py`
- 実行系コマンド:
  - `src/mudsync/commands/build.py`: リモート `docker build`
  - `src/mudsync/commands/run.py`: リモート `docker run`
  - `src/mudsync/commands/jupyter.py`: Jupyter 起動 + token 取得 + port forward
- 同期系:
  - `src/mudsync/commands/sync.py`: rsync 同期
  - `src/mudsync/commands/manage.py`: 同期ルール管理

## Current status
- 種別: plan 実行中
- 受領指示: 「指示に従い、planを立てなさい」
- 完了済み:
  - `agents/readme.md` を読み、要求を整理
  - Docker Compose 公式仕様（`compose run --rm`, `--build`）を確認
  - 追加合意を反映して計画を更新
    - `run`: `COMMAND` 必須 + `--build` 明示時のみ再ビルド
    - service 未指定時は先頭 service 自動採用
    - compose ファイル既定は `compose.yaml` 優先探索
    - `jupyter`: `start/stop` サブコマンド化（start=`up -d`, stop=`down`）
    - `jupyter start` は URL 出力のみ（port forward は保留）
  - 計画文書を作成
    - `agents/plans/plan.md`
    - `agents/plans/spec.md`
    - `agents/plans/tasks/01_cli_surface_cleanup.md`
    - `agents/plans/tasks/02_run_compose_migration.md`
    - `agents/plans/tasks/03_jupyter_refactor.md`
    - `agents/plans/tasks/04_tests_and_regression.md`
- 現在作業中: なし（計画作成フェーズ完了）
- 現在の課題:
  - `jupyter start` の URL 抽出失敗時フォールバック表示方針を実装時に確定する必要あり
- 次のステップ:
  1. Task 01 から順に実装開始
