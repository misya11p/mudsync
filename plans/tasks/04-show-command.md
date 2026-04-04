# Task 4: Show コマンド

## 概要

現在の設定に基づくSSH接続情報を表示する `mudsync show` コマンドを実装する。

## 実施内容

### 4.1 ファイル: `src/mudsync/commands/show.py`

```python
import typer
from mudsync.config import require_config
from mudsync.ssh_config import get_host_config


def command():
    """SSH接続情報を表示する"""
    app_config = require_config()
    ssh_info = get_host_config(app_config.ssh_host)

    typer.echo(f"Host:       {ssh_info.host}")
    typer.echo(f"IP:         {ssh_info.hostname}")
    typer.echo(f"User:       {ssh_info.user}")
    typer.echo(f"Port:       {ssh_info.port}")
    typer.echo(f"SSH Key:    {ssh_info.identity_file or '(not set)'}")
    typer.echo(f"Remote Home: {app_config.remote_home}")
```

### 4.2 CLIへの登録

`src/mudsync/cli.py` に追記:

```python
from mudsync.commands import show as show_cmd

@app.command()
def show():
    """Show current SSH connection settings"""
    show_cmd.command()
```

## 出力例

```
$ mudsync show
Host:        gpu-server-01
IP:          192.168.1.100
User:        myuser
Port:        22
SSH Key:     /Users/k/.ssh/id_ed25519
Remote Home: /home/myuser
```

## 成果物

- `src/mudsync/commands/show.py` - showコマンド実装
- `src/mudsync/cli.py` - CLIエントリーポイント（更新）

## 検証

```bash
uv run mudsync show
# 上記の出力例のように表示される

# 未設定時のテスト
rm ~/.config/mudsync/config.json
uv run mudsync show
# Error: Config not set. Run 'mudsync config' first.
```
