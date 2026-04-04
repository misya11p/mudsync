import re
import subprocess
import time

import typer

from mudsync.commands.build import build_container_name
from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import SSHHost, get_host_config


def command(port: int = typer.Option(8888, "--port", "-p", help="Local port number")):
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    container_name = build_container_name(
        ssh_info.user, app_config.remote_home, proj_name
    )

    remote_path = f"{app_config.remote_home}/{proj_name}"

    typer.echo(f"Starting Jupyter Lab on {ssh_info.hostname}...")
    typer.echo(f"Port: {port}")
    typer.echo()

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
        raise SystemExit(f"Error: Failed to start Jupyter Lab.\nstderr: {e.stderr}")
    except FileNotFoundError:
        raise SystemExit("Error: ssh command not found")

    typer.echo("Waiting for Jupyter Lab to start...")
    time.sleep(5)

    token = get_jupyter_token(ssh_info, container_id)

    typer.echo()
    typer.echo(f"Jupyter Lab URL: http://localhost:{port}/?token={token}")
    typer.echo()
    typer.echo("Starting port forwarding... (Press Ctrl+C to stop)")

    forward_cmd = [
        "ssh",
        "-L",
        f"{port}:localhost:{port}",
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


def get_jupyter_token(ssh_info: SSHHost, container_id: str) -> str:
    ssh_cmd = [
        "ssh",
    ]
    if ssh_info.port != 22:
        ssh_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        ssh_cmd.extend(["-i", ssh_info.identity_file])
    ssh_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}")

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
                match = re.search(r"token=([a-f0-9]+)", output)
                if match:
                    return match.group(1)
        except subprocess.CalledProcessError:
            pass

        time.sleep(2)

    return ""
