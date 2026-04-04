# Task 3: Config コマンド

## 概要

対話的にGPUサーバーの接続情報を設定する `mudsync config` コマンドを実装する。

## 実施内容

### 3.1 ファイル: `src/mudsync/config.py`

アプリ設定の読み書きを担当するモジュール。

```python
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class AppConfig(BaseModel):
    """アプリケーション設定"""
    ssh_host: str           # 選択されたSSHホスト名
    remote_home: str        # リモートサーバー上のユーザーホームディレクトリ


def get_config_dir() -> Path:
    """設定ディレクトリを返す ($XDG_CONFIG_HOME/mudsync)"""
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "mudsync"


def load_config() -> Optional[AppConfig]:
    """設定ファイルを読み込む。未設定ならNoneを返す"""
    config_path = get_config_dir() / "config.json"
    if not config_path.exists():
        return None
    return AppConfig.model_validate_json(config_path.read_text())


def save_config(config: AppConfig) -> None:
    """設定ファイルを保存"""
    config_path = get_config_dir() / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config.model_dump_json(indent=2))


def require_config() -> AppConfig:
    """設定が存在することを保証。なければエラー"""
    config = load_config()
    if config is None:
        raise RuntimeError("Config not set. Run 'mudsync config' first.")
    return config
```

**注意:** pydanticはtyperに同梱されていないため、dataclassを使用する方が依存が少ない。以下で実装:

```python
from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    ssh_host: str
    remote_home: str


def get_config_dir() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "mudsync"


def load_config() -> Optional[AppConfig]:
    config_path = get_config_dir() / "config.json"
    if not config_path.exists():
        return None
    data = json.loads(config_path.read_text())
    return AppConfig(**data)


def save_config(config: AppConfig) -> None:
    config_path = get_config_dir() / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(asdict(config), indent=2))


def require_config() -> AppConfig:
    config = load_config()
    if config is None:
        raise SystemExit("Error: Config not set. Run 'mudsync config' first.")
    return config
```

### 3.2 ファイル: `src/mudsync/commands/config.py`

```python
import typer
from InquirerPy import inquirer
from InquirerPy.validator import PathValidator
from mudsync.config import AppConfig, save_config
from mudsync.ssh_config import list_hosts


def command():
    """対話的に設定を行う"""
    # ホスト一覧取得
    hosts = list_hosts()
    if not hosts:
        raise SystemExit("Error: No SSH hosts found in ~/.ssh/config")

    # ホスト選択
    ssh_host = inquirer.select(
        message="Select SSH host:",
        choices=hosts,
    ).execute()

    # リモートホームディレクトリ入力
    remote_home = inquirer.text(
        message="Remote home directory:",
        default="/home",
        # バリデーション: /で始まる絶対パス
    ).execute()

    # 保存
    config = AppConfig(ssh_host=ssh_host, remote_home=remote_home)
    save_config(config)

    typer.echo(f"Config saved: {ssh_host} -> {remote_home}")
```

### 3.3 CLIへの登録: `src/mudsync/cli.py`

```python
import typer
from mudsync.commands import config as config_cmd

app = typer.Typer(help="MUDSync - GPU server synchronization CLI")

@app.command()
def config():
    """Configure GPU server connection settings"""
    config_cmd.command()

if __name__ == "__main__":
    app()
```

## 成果物

- `src/mudsync/config.py` - 設定管理モジュール
- `src/mudsync/commands/config.py` - configコマンド実装
- `src/mudsync/cli.py` - CLIエントリーポイント（更新）

## 検証

```bash
# 対話実行
uv run mudsync config
# > ホスト一覧が表示される
# > ホストを選択
# > リモートホームを入力
# > 設定が保存される

# 設定ファイル確認
cat ~/.config/mudsync/config.json
# {"ssh_host": "gpu-server-01", "remote_home": "/home/myuser"}
```
