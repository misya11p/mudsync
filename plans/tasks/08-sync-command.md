# Task 8: Sync コマンド

## 概要

ローカルのプロジェクトディレクトリとGPUサーバー上の `{remote_home}/proj_name` をrsyncで同期する `mudsync sync` コマンドを実装する。

## 実施内容

### 8.1 ファイル: `src/mudsync/commands/sync.py`

```python
import subprocess
import typer

from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config
from mudsync.sync_rules import get_excludes


def command():
    """ローカルプロジェクトをGPUサーバーとrsyncで同期する"""
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    # リモート側のパス
    remote_path = f"{app_config.remote_home}/{proj_name}"

    # rsyncコマンドを構築
    rsync_cmd = [
        "rsync",
        "-avz",  # archive, verbose, compress
    ]

    # 除外ルールを適用
    excludes = get_excludes(project_root)
    for exclude in excludes:
        rsync_cmd.extend(["--exclude", exclude])

    # SSHオプション
    ssh_opts = f"-o StrictHostKeyChecking=no"
    if ssh_info.port != 22:
        ssh_opts += f" -p {ssh_info.port}"
    if ssh_info.identity_file:
        ssh_opts += f" -i {ssh_info.identity_file}"

    rsync_cmd.extend(["-e", f"ssh {ssh_opts}"])

    # ソースとデスティネーション
    # ソース末尾の / は重要（ディレクトリの中身を送る）
    rsync_cmd.append(f"{project_root}/")
    rsync_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}:{remote_path}/")

    # 実行
    typer.echo(f"Syncing {project_root} -> {ssh_info.user}@{ssh_info.hostname}:{remote_path}/")
    typer.echo(f"Excludes: {len(excludes)} rules")
    typer.echo()

    try:
        result = subprocess.run(rsync_cmd, check=True)
        typer.echo()
        typer.echo("Sync completed successfully.")
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Error: rsync failed with exit code {e.returncode}")
    except FileNotFoundError:
        raise SystemExit(
            "Error: rsync not found. Please install rsync:\n"
            "  macOS: brew install rsync\n"
            "  Ubuntu: sudo apt install rsync"
        )
```

### 8.2 設計上の決定

- **rsync `-a`**: archiveモード（再帰、シンボリックリンク、パーミッション、タイムスタンプ等を保持）。rsyncアルゴリズムによる差分転送が自動適用される
- **rsync `-v`**: 転送状況を表示
- **rsync `-z`**: 転送時に圧縮。ネットワーク帯域を節約
- **除外ルール**: `manage` で設定された除外リストを `--exclude` に渡す
- **StrictHostKeyChecking=no**: 初回接続時のホストキー確認をスキップ（既にSSH接続可能な前提）
- **ソースパス末尾の `/`**: `{project_root}/` とすることで、ディレクトリ自体ではなく中身を送る

### 8.3 転送フロー

```
ローカル: /Users/k/projects/my-ml-project/
  ├── src/
  ├── train.py
  └── Dockerfile

↓ rsync -avz --exclude='data/' --exclude='.git/'

リモート: /home/myuser/my-ml-project/
  ├── src/
  ├── train.py
  └── Dockerfile
```

### 8.4 CLIへの登録

`src/mudsync/cli.py` に追記:

```python
from mudsync.commands import sync as sync_cmd

@app.command()
def sync():
    """Sync local project to GPU server via rsync"""
    sync_cmd.command()
```

## 成果物

- `src/mudsync/commands/sync.py` - syncコマンド実装
- `src/mudsync/cli.py` - CLIエントリーポイント（更新）

## 検証

```bash
cd ~/projects/my-ml-project
uv run mudsync sync
# Syncing /Users/k/projects/my-ml-project -> myuser@gpu-server:/home/myuser/my-ml-project/
# Excludes: 2 rules
#
# sending incremental file list
# src/model.py
# src/utils.py
# train.py
#
# Sync completed successfully.

# 2回目の実行（変更なし）
uv run mudsync sync
# sending incremental file list
# （差分なし）
# Sync completed successfully.
```
