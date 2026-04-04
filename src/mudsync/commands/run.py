import shlex
import subprocess

import typer

from mudsync.commands.build import build_container_name
from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config


def command(cmd: str | None = None):
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    container_name = build_container_name(
        ssh_info.user, app_config.remote_home, proj_name
    )

    remote_path = f"{app_config.remote_home}/{proj_name}"

    docker_cmd = [
        "docker",
        "run",
        "--gpus",
        "all",
        "-it",
        "--rm",
        "-v",
        f"{remote_path}:/workspace",
        "-w",
        "/workspace",
    ]

    if cmd:
        docker_cmd.extend([container_name] + shlex.split(cmd))
    else:
        docker_cmd.append(container_name)

    ssh_cmd = [
        "ssh",
    ]
    if ssh_info.port != 22:
        ssh_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        ssh_cmd.extend(["-i", ssh_info.identity_file])

    ssh_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}")

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
