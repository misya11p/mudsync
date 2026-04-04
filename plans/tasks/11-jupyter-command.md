# Task 11: Jupyter コマンド

## 概要

GPUサーバー上でJupyter Labを起動し、SSHポートフォワーディング経由でアクセスできるようにする `mudsync jupyter` コマンドを実装する。

## 実施内容

### 11.1 ファイル: `src/mudsync/commands/jupyter.py`

```python
import subprocess
import time
import re

import typer

from mudsync.commands.build import build_container_name
from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config


def command(port: int = 8888):
    """
    GPUサーバー上でJupyter Labを起動し、ポートフォワーディングURLを出力する。

    Args:
        port: ローカルで使用するポート番号（デフォルト: 8888）
    """
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    # コンテナ名
    container_name = build_container_name(
        ssh_info.user, app_config.remote_home, proj_name
    )

    # リモート側のパス
    remote_path = f"{app_config.remote_home}/{proj_name}"

    typer.echo(f"Starting Jupyter Lab on {ssh_info.hostname}...")
    typer.echo(f"Port: {port}")
    typer.echo()

    # Step 1: サーバー上でJupyter Labをバックグラウンドで起動
    jupyter_cmd = (
        f"docker run --gpus all -d --rm "
        f"-v {remote_path}:/workspace "
        f"-w /workspace "
        f"-p {port}:8888 "
        f"{container_name} "
        f"jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root"
    )

    ssh_cmd = [
        "ssh",
    ]
    if ssh_info.port != 22:
        ssh_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        ssh_cmd.extend(["-i", ssh_info.identity_file])
    ssh_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}")
    ssh_cmd.append(jupyter_cmd)

    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        container_id = result.stdout.strip()
        typer.echo(f"Jupyter container started: {container_id[:12]}")
    except subprocess.CalledProcessError as e:
        raise SystemExit(
            f"Error: Failed to start Jupyter Lab.\n"
            f"stderr: {e.stderr}"
        )
    except FileNotFoundError:
        raise SystemExit("Error: ssh command not found")

    # Step 2: Jupyterが起動するのを待つ
    typer.echo("Waiting for Jupyter Lab to start...")
    time.sleep(5)

    # Step 3: トークンを取得
    token = get_jupyter_token(ssh_info, container_id)

    # Step 4: ポートフォワーディングを開始
    typer.echo()
    typer.echo(f"Jupyter Lab URL: http://localhost:{port}/?token={token}")
    typer.echo()
    typer.echo("Starting port forwarding... (Press Ctrl+C to stop)")

    forward_cmd = [
        "ssh",
        "-L", f"{port}:localhost:{port}",
    ]
    if ssh_info.port != 22:
        forward_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        forward_cmd.extend(["-i", ssh_info.identity_file])
    forward_cmd.extend([f"{ssh_info.user}@{ssh_info.hostname}", "-N"])

    try:
        subprocess.run(forward_cmd, check=True)
    except KeyboardInterrupt:
        typer.echo("\nPort forwarding stopped.")
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Error: Port forwarding failed: {e}")


def get_jupyter_token(ssh_info, container_id: str) -> str:
    """
    Jupyterコンテナからトークンを取得する。

    docker logsからtoken=を抽出する。
    """
    ssh_cmd = [
        "ssh",
    ]
    if ssh_info.port != 22:
        ssh_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        ssh_cmd.extend(["-i", ssh_info.identity_file])
    ssh_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}")

    # docker logsからトークン抽出
    log_cmd = f"docker logs {container_id} 2>&1 | grep -oP 'token=[a-f0-9]+' | head -1"
    ssh_cmd.append(log_cmd)

    for attempt in range(10):
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.strip()
            if output:
                # token=xxx の形式からトークン部分を抽出
                match = re.search(r"token=([a-f0-9]+)", output)
                if match:
                    return match.group(1)
        except subprocess.CalledProcessError:
            pass

        time.sleep(2)

    # トークンが取得できない場合、空文字を返す（トークンなしアクセスを試みる）
    return ""
```

### 11.2 動作フロー

```
1. ユーザー: mudsync jupyter --port 9999
2. サーバー上で docker run -d ... jupyter lab を実行
3. コンテナが起動するのを待つ（5秒）
4. docker logs から token=xxx を抽出
5. URLを出力: http://localhost:9999/?token=xxx
6. ssh -L 9999:localhost:9999 ... -N でポートフォワーディング開始
7. Ctrl+C でフォワード終了（Jupyterコンテナはサーバー上で動き続ける）
```

### 11.3 設計上の決定

- **detached mode (`-d`)**: Jupyterをバックグラウンドで起動。フォワードのみをフォアグラウンドで維持
- **トークン取得**: `docker logs` から正規表現で抽出。最大10回・2秒間隔でリトライ
- **フォアグラウンドフォワード**: `ssh -L ... -N` をフォアグラウンドで実行。Ctrl+Cで切断
- **コンテナの永続性**: `--rm` 付きなので、ユーザーが明示的に停止しない限り動き続ける。フォワード切断後もJupyterはアクセス可能（直接サーバーIP:portで）

### 11.4 改善の余地

- トークンなしモードのオプション: `--no-token` で `--NotebookApp.token=''` を追加
- フォアグラウンドではなくバックグラウンドでフォワードするオプション
- Jupyter停止コマンドの追加

### 11.5 CLIへの登録

`src/mudsync/cli.py` に追記:

```python
from mudsync.commands import jupyter as jupyter_cmd

@app.command()
def jupyter(port: int = typer.Option(8888, "--port", "-p", help="Local port number")):
    """Start Jupyter Lab on GPU server with port forwarding"""
    jupyter_cmd.command(port)
```

## 成果物

- `src/mudsync/commands/jupyter.py` - jupyterコマンド実装
- `src/mudsync/cli.py` - CLIエントリーポイント（更新）

## 検証

```bash
cd ~/projects/my-ml-project
uv run mudsync jupyter --port 9999
# Starting Jupyter Lab on 192.168.1.100...
# Port: 9999
#
# Jupyter container started: abc123def456
# Waiting for Jupyter Lab to start...
#
# Jupyter Lab URL: http://localhost:9999/?token=abc123def456...
#
# Starting port forwarding... (Press Ctrl+C to stop)
# ^C
# Port forwarding stopped.
```
