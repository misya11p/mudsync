# Task 9: Build コマンド

## 概要

GPUサーバー上でDockerイメージをビルドする `mudsync build` コマンドを実装する。

## 実施内容

### 9.1 ファイル: `src/mudsync/commands/build.py`

```python
import subprocess

import typer

from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config


def build_container_name(ssh_user: str, remote_home: str, proj_name: str) -> str:
    """
    コンテナ名を生成する。

    形式: {user}_{remote_home_basename}_{proj_name}
    例: myuser_home_my-ml-project
    """
    # remote_home の最後のディレクトリ名を取得
    # /home/myuser -> myuser, /data -> data
    home_basename = remote_home.rstrip("/").split("/")[-1]
    return f"{ssh_user}_{home_basename}_{proj_name}"


def command():
    """GPUサーバー上でDockerイメージをビルドする"""
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    # Dockerfileの存在確認（ローカル）
    dockerfile = project_root / "Dockerfile"
    if not dockerfile.exists():
        raise SystemExit(
            f"Error: Dockerfile not found in {project_root}\n"
            "Please create a Dockerfile before running build."
        )

    # コンテナ名
    container_name = build_container_name(
        ssh_info.user, app_config.remote_home, proj_name
    )

    # リモート側のパス
    remote_path = f"{app_config.remote_home}/{proj_name}"

    # SSH経由でリモートでdocker buildを実行
    ssh_cmd = [
        "ssh",
    ]
    if ssh_info.port != 22:
        ssh_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        ssh_cmd.extend(["-i", ssh_info.identity_file])

    ssh_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}")

    remote_cmd = (
        f"cd {remote_path} && "
        f"docker build -t {container_name} ."
    )
    ssh_cmd.append(remote_cmd)

    typer.echo(f"Building Docker image on {ssh_info.hostname}...")
    typer.echo(f"Container name: {container_name}")
    typer.echo(f"Build context: {remote_path}")
    typer.echo()

    try:
        result = subprocess.run(ssh_cmd, check=True)
        typer.echo()
        typer.echo(f"Successfully built: {container_name}")
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Error: Docker build failed with exit code {e.returncode}")
    except FileNotFoundError:
        raise SystemExit("Error: ssh command not found")
```

### 9.2 コンテナ名生成ロジック

| 項目 | 値 | 例 |
|------|-----|-----|
| ssh_user | .ssh/configのUser | `myuser` |
| remote_home | アプリ設定 | `/home/myuser` |
| home_basename | remote_homeの末尾ディレクトリ | `myuser` |
| proj_name | プロジェクトルートディレクトリ名 | `my-ml-project` |
| **コンテナ名** | `{user}_{home_basename}_{proj_name}` | `myuser_myuser_my-ml-project` |

**注意:** remote_homeが `/home` の場合は `home` になる。仕様では `/home/username` を想定しているので、`myuser_home_my-ml-project` のような形になる。

### 9.3 CLIへの登録

`src/mudsync/cli.py` に追記:

```python
from mudsync.commands import build as build_cmd

@app.command()
def build():
    """Build Docker image on GPU server"""
    build_cmd.command()
```

## 成果物

- `src/mudsync/commands/build.py` - buildコマンド実装
- `src/mudsync/cli.py` - CLIエントリーポイント（更新）

## 検証

```bash
cd ~/projects/my-ml-project
uv run mudsync build
# Building Docker image on 192.168.1.100...
# Container name: myuser_home_my-ml-project
# Build context: /home/myuser/my-ml-project
#
# Sending build context to Docker daemon  2.048kB
# Step 1/5 : FROM nvidia/cuda:12.1-runtime-ubuntu22.04
# ...
# Successfully built: myuser_home_my-ml-project

# Dockerfileなし
rm Dockerfile
uv run mudsync build
# Error: Dockerfile not found in /Users/k/projects/my-ml-project
```
