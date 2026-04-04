# Task 1: プロジェクトセットアップ

## 概要

pyproject.tomlの設定更新、依存ライブラリのインストール、ディレクトリ構造の作成を行う。

## 実施内容

### 1.1 pyproject.tomlの更新

```toml
[project]
name = "mudsync"
version = "0.1.0"
description = "CLI tool for GPU server synchronization"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "typer>=0.12",
    "inquirerpy>=0.3",
]

[project.scripts]
mudsync = "mudsync.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 1.2 ディレクトリ構造の作成

```bash
mkdir -p src/mudsync/commands
touch src/mudsync/__init__.py
touch src/mudsync/__main__.py
touch src/mudsync/cli.py
touch src/mudsync/config.py
touch src/mudsync/ssh_config.py
touch src/mudsync/project.py
touch src/mudsync/sync_rules.py
touch src/mudsync/commands/__init__.py
```

### 1.3 依存ライブラリのインストール

```bash
uv sync
```

### 1.4 動作確認

```bash
uv run mudsync --help
```

空のTyperアプリが表示されれば成功。

## 成果物

- 更新された `pyproject.toml`
- 空のモジュールファイル群
- 依存ライブラリがインストールされた `.venv`

## 検証

```bash
uv run mudsync --help
# Usage: mudsync [OPTIONS] COMMAND [ARGS]...
```
