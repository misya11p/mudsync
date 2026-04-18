import subprocess
import tempfile
from pathlib import Path

import typer

from mudsync.project import require_project
from mudsync.ssh_config import SSHHost
from mudsync.ssh_config import get_host_config
from mudsync.sync_rules import get_excludes, require_project_config


def build_rsync_ssh_option(ssh_info: SSHHost) -> str:
    ssh_opts = "-o StrictHostKeyChecking=no"
    if ssh_info.port != 22:
        ssh_opts += f" -p {ssh_info.port}"
    if ssh_info.identity_file:
        ssh_opts += f" -i {ssh_info.identity_file}"
    return f"ssh {ssh_opts}"


def build_rsync_command(
    source: Path | str,
    destination: str,
    ssh_info: SSHHost,
    options: list[str] | None = None,
) -> list[str]:
    rsync_cmd = ["rsync", "-avz", *(options or [])]
    rsync_cmd.extend(["-e", build_rsync_ssh_option(ssh_info)])
    rsync_cmd.append(str(source))
    rsync_cmd.append(destination)
    return rsync_cmd


def run_rsync(rsync_cmd: list[str]) -> None:
    try:
        subprocess.run(rsync_cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Error: rsync failed with exit code {e.returncode}") from e
    except FileNotFoundError as exc:
        raise SystemExit(
            "Error: rsync not found. Please install rsync:\n"
            "  macOS: brew install rsync\n"
            "  Ubuntu: sudo apt install rsync"
        ) from exc


def command():
    project_root = require_project()
    project_config = require_project_config(project_root)
    ssh_info = get_host_config(project_config.server)

    remote_path = project_config.remote_path

    excludes = get_excludes(project_root)
    exclude_lines = list(excludes)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("\n".join(exclude_lines) + "\n")
        exclude_file = f.name

    rsync_cmd = build_rsync_command(
        source=f"{project_root}/",
        destination=f"{ssh_info.user}@{ssh_info.hostname}:{remote_path}/",
        ssh_info=ssh_info,
        options=["--delete", "--exclude-from", exclude_file],
    )

    typer.echo(
        f"Syncing {project_root} -> {ssh_info.user}@{ssh_info.hostname}:{remote_path}/"
    )
    typer.echo(f"Excludes: {len(exclude_lines)} rules")
    typer.echo()

    try:
        run_rsync(rsync_cmd)
        typer.echo()
        typer.echo("Sync completed successfully.")
    finally:
        import os

        os.unlink(exclude_file)
