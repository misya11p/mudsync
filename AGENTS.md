# AGENTS.md

本リポジトリの説明

## 目的

- ローカルのプロジェクトディレクトリとリモートサーバー上の対応するディレクトリのファイルと環境を同期するための CLI ツール
- rsync を活用して、変更されたファイルのみを転送する
- docker composeを用いて環境を管理する

## プロジェクトの実体
- Python CLI ツール（パッケージ: `mudsync`）。実装は `src/mudsync/` 配下。
- CLI エントリは `msync`（`pyproject.toml` の `[project.scripts]`）。
- Python 要件は **3.13+**（`.python-version` は `3.13`）。
- 主要コマンド定義は `src/mudsync/cli.py`。

## コード構造（変更前に把握）
- 全体同期（local -> remote）: `src/mudsync/commands/sync.py`
  - `rsync --delete --exclude-from <tmpfile>` を使う。
- 部分転送: `src/mudsync/commands/push.py` / `src/mudsync/commands/pull.py`
  - include ルール方式（`--include=*/`, `--include=<pattern>...`, `--exclude=*`）。
- 実行系: `src/mudsync/commands/run.py`
  - `--sync` 指定時は先に `sync` を実行してから service 解決する。
  - service 未指定時はリモートで `docker compose config --services` の先頭 service を使う。
- compose/ssh 補助: `src/mudsync/commands/compose.py`
- 設定保存: `src/mudsync/config.py`（`$XDG_CONFIG_HOME/mudsync/config.json`）
- プロジェクト別除外: `src/mudsync/sync_rules.py`（`$XDG_STATE_HOME/mudsync/sync_rules/<hash>.json`）

## 仕様上の注意（既存挙動）
- `build` サブコマンドは CLI から外れている（`msync --help` に出ない）。`src/mudsync/commands/build.py` は残存ファイル。
- 多くのコマンドは「git 管理下ディレクトリ内」での実行前提（`require_project()`）。
- `config` / `info` / `connect` / `sync` / `push` / `pull` / `run` は `~/.ssh/config` と事前 `msync config` 設定を前提にする。
- `manage` は初期表示時に「大きいファイル（>10MB）」や「要素数が多いディレクトリ（>100）」を除外候補へ自動追加する。

## 変更時の実務ルール（この repo 向け）
- CLI を触るときは `src/mudsync/cli.py` と対応する `tests/test_cli_and_run.py` をセットで更新。
- rsync 挙動を触るときは `tests/test_sync_push_pull.py` の方向（push=local->remote, pull=remote->local）と option 順序を維持。
- 変更後は最低でも該当テスト + 全テストを `unittest` コマンドで確認する。
