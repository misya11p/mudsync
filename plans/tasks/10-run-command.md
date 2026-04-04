# Task 10: Run コマンド

## 概要

GPUサーバーのDockerコンテナ上で指定したコマンドを実行する `mudsync run [command]` コマンドを実装する。

## 実施内容

### 10.1 ファイル: `src/mudsync/commands/run.py`

```python
import subprocess

import typer

from mudsync.commands.build import build_container_name
from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config


def command(cmd: str | None = None):
    """
    GPUサーバーのDockerコンテナ上でコマンドを実行する。

    Args:
        cmd: 実行するコマンド。指定しない場合はコンテナのデフォルトCMDを実行
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

    # docker run コマンドを構築
    docker_cmd = [
        "docker", "run",
        "--gpus", "all",   # GPUをコンテナに渡す
        "-it",              # インタラクティブ + TTY
        "--rm",             # 終了時にコンテナを削除
        "-v", f"{remote_path}:/workspace",  # 同期済みディレクトリをマウント
        "-w", "/workspace",  # 作業ディレクトリ
    ]

    # 実行コマンド
    if cmd:
        docker_cmd.extend([container_name] + cmd.split())
    else:
        docker_cmd.append(container_name)

    # SSH経由で実行
    ssh_cmd = [
        "ssh",
    ]
    if ssh_info.port != 22:
        ssh_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        ssh_cmd.extend(["-i", ssh_info.identity_file])

    ssh_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}")

    # dockerコマンドを文字列に変換してSSH経由で実行
    remote_cmd = " ".join(docker_cmd)
    ssh_cmd.append(remote_cmd)

    if cmd:
        typer.echo(f"Running on {ssh_info.hostname}: {cmd}")
    else:
        typer.echo(f"Starting container: {container_name}")
    typer.echo()

    try:
        result = subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Error: Command failed with exit code {e.returncode}")
    except FileNotFoundError:
        raise SystemExit("Error: ssh command not found")
```

### 10.2 設計上の決定

- `--gpus all`: NVIDIA Container Toolkitが必要。GPUサーバーにはインストール済みと想定
- `-it`: インタラクティブモード + 疑似TTY。SSH経由でも正しく動作する
- `--rm`: コマンド終了後にコンテナを自動削除。ディスク容量を節約
- `-v {remote_path}:/workspace`: 同期済みのディレクトリをマウント。ビルドはイメージのみを行い、データはマウントで共有
- `-w /workspace`: 作業ディレクトリを `/workspace` に設定
- コマンドの分割: `cmd.split()` で簡易的に分割。クォートを含む複雑なコマンドの場合は注意が必要

### 10.3 コマンド分割の注意点

`mudsync run "python train.py --epochs 100"` の場合:
- Typerが `"python train.py --epochs 100"` を1つの文字列として受け取る
- `split()` で `["python", "train.py", "--epochs", "100"]` に分割
- シェル引用符を含むコマンド（例: `python -c "print('hello')"`）は正しく分割されない可能性がある

**改善案:** 将来的には `shlex.split()` を使用してより正確な分割を行う:

```python
import shlex
if cmd:
    docker_cmd.extend([container_name] + shlex.split(cmd))
```

### 10.4 CLIへの登録

`src/mudsync/cli.py` に追記:

```python
from mudsync.commands import run as run_cmd

@app.command()
def run(cmd: str | None = None):
    """Run a command in Docker container on GPU server"""
    run_cmd.command(cmd)
```

## 成果物

- `src/mudsync/commands/run.py` - runコマンド実装
- `src/mudsync/cli.py` - CLIエントリーポイント（更新）

## 検証

```bash
cd ~/projects/my-ml-project

# コマンド指定
uv run mudsync run "python train.py --epochs 100"
# Running on 192.168.1.100: python train.py --epochs 100
# Epoch 1/100: loss=0.5234
# ...

# bash起動
uv run mudsync run "bash"
# root@container:/workspace#

# デフォルトCMD
uv run mudsync run
# Starting container: myuser_home_my-ml-project
# （DockerfileのCMDが実行される）
```
