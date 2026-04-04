# Task 6: Connect コマンド

## 概要

GPUサーバーにSSH接続し、プロジェクトディレクトリに移動した状態でインタラクティブシェルを提供する `mudsync connect` コマンドを実装する。

## 実施内容

### 6.1 ファイル: `src/mudsync/commands/connect.py`

```python
import os
import subprocess
import sys

import typer

from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config


def command():
    """
    GPUサーバーにSSH接続し、プロジェクトディレクトリにcdした状態で
    インタラクティブシェルを提供する。
    """
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    # リモート側のプロジェクトパス
    remote_path = f"{app_config.remote_home}/{proj_name}"

    # SSHコマンドを構築
    ssh_cmd = [
        "ssh",
        "-t",  # 疑似TTYを強制
    ]

    # SSHオプション
    if ssh_info.port != 22:
        ssh_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        ssh_cmd.extend(["-i", ssh_info.identity_file])

    # user@host
    ssh_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}")

    # リモートで実行するコマンド: cdしてシェル起動
    remote_cmd = f"cd {remote_path} && exec $SHELL"
    ssh_cmd.append(remote_cmd)

    # SSHプロセスを実行（現在のプロセスを置き換え）
    try:
        os.execvp(ssh_cmd[0], ssh_cmd)
    except OSError as e:
        raise SystemExit(f"Error: Failed to execute SSH: {e}")
```

### 6.2 設計上の決定

- `os.execvp` を使用してPythonプロセスをsshプロセスに置き換える
  - メリット: ssh終了時に自動的にローカルシェルに戻る。余計なプロセスが残らない
  - `exec` は現在のプロセスを置き換えるため、sshが終了するとそのままコマンドが終了する
- `-t` オプションで疑似TTYを強制。これがないとリモートシェルが正しく動作しない
- `exec $SHELL` でログインシェルのデフォルトシェルを起動

### 6.3 CLIへの登録

`src/mudsync/cli.py` に追記:

```python
from mudsync.commands import connect as connect_cmd

@app.command()
def connect():
    """SSH connect to GPU server and cd to project directory"""
    connect_cmd.command()
```

## 成果物

- `src/mudsync/commands/connect.py` - connectコマンド実装
- `src/mudsync/cli.py` - CLIエントリーポイント（更新）

## 検証

```bash
cd ~/projects/my-ml-project
uv run mudsync connect
# SSH接続が確立され、リモートで ~/my-ml-project にcdした状態のシェルが起動
# myuser@gpu-server:~/my-ml-project$
# exit でローカルに戻る
```
