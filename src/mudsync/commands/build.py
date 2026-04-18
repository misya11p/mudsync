import subprocess

import typer

from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config


def build_container_name(ssh_user: str, remote_path: str, proj_name: str) -> str:
    path_basename = remote_path.rstrip("/").split("/")[-1]
    return f"{ssh_user}_{path_basename}_{proj_name}"


def command():
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    dockerfile = project_root / "Dockerfile"
    if not dockerfile.exists():
        raise SystemExit(
            f"Error: Dockerfile not found in {project_root}\n"
            "Please create a Dockerfile before running build."
        )

    container_name = build_container_name(
        ssh_info.user, app_config.remote_path, proj_name
    )

    remote_path = f"{app_config.remote_path}/{proj_name}"

    ssh_cmd = [
        "ssh",
    ]
    if ssh_info.port != 22:
        ssh_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        ssh_cmd.extend(["-i", ssh_info.identity_file])

    ssh_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}")

    remote_cmd = f"cd {remote_path} && docker build -t {container_name} ."
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
