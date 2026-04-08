## Project overview
- `mudsync` は GPU サーバー連携用の Python CLI。
- 主要コマンドは `config`, `info`, `connect`, `manage`, `sync`, `push`, `pull`, `run`。
- 同期機能は rsync ベースで、`sync` は project 全体同期（local -> remote）として運用。

## Code explanations
- CLI エントリ: `src/mudsync/cli.py`
- 同期系:
  - `src/mudsync/commands/sync.py`: project 全体同期（exclude-from 方式） + rsync 共通ヘルパー
  - `src/mudsync/commands/push.py`: include ベースの filtered 転送（local -> remote）
  - `src/mudsync/commands/pull.py`: include ベースの filtered 転送（remote -> local）
  - `src/mudsync/commands/manage.py`: `sync` 向け除外ルールの管理
  - `src/mudsync/sync_rules.py`: プロジェクト別除外ルールの保存/読込
- 実行系:
  - `src/mudsync/commands/run.py`: `docker compose run --rm` 実行
- テスト:
  - `tests/test_cli_and_run.py`: push/pull CLI 公開面のテストを追加
  - `tests/test_sync_push_pull.py`: push/pull include 順序・転送方向・sync 回帰テスト

## Current status
- 種別: agent 実装
- 受領指示:
  1. `agents/` を読み、実装を完了させる
  2. `jupyter` コマンドを一旦削除する
- 完了済み:
  - Task 01: `cli.py` に `push` / `pull` を追加、`manage` ヘルプを sync 用文言へ更新
  - Task 02: `sync.py` に rsync 共通ヘルパー（SSH option 生成、コマンド組立、実行）を実装
  - Task 03: `push.py` / `pull.py` を新規追加し、include ベース filtered 転送を実装
  - Task 04: テストを追加・更新し、`sync` 回帰を含めて実行完了
  - テスト実行結果: `uv run python -m unittest discover -s tests -p 'test_*.py'` で 33 件すべて成功
  - `jupyter` コマンドを CLI から削除
  - `src/mudsync/commands/jupyter.py` を削除
  - `tests/test_jupyter.py` を削除
- 現在作業中:
  - なし
- 現在の課題:
  - なし
- 次のステップ:
  1. 実機（GPU サーバー）で `push` / `pull` の dry-run 相当確認
  2. 必要なら push/pull の表示文言を運用トーンに合わせて微調整
