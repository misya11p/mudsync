import shlex
import subprocess
import tempfile
from pathlib import Path

import typer

from mudsync.commands.compose import build_ssh_command
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


def run_rsync(rsync_cmd: list[str], verbose: bool = False) -> None:
    if verbose:
        typer.echo(f"$ {shlex.join(rsync_cmd)}")
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


def run_ssh_command(ssh_info: SSHHost, remote_command: str, verbose: bool = False) -> None:
    ssh_cmd = build_ssh_command(ssh_info, remote_command)
    if verbose:
        typer.echo(f"$ {shlex.join(ssh_cmd)}")
    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(
            f"Error: SSH command failed with exit code {e.returncode}"
        ) from e
    except FileNotFoundError as exc:
        raise SystemExit("Error: ssh command not found") from exc


def command(verbose: bool = False):
    project_root = require_project()
    project_config = require_project_config(project_root)
    ssh_info = get_host_config(project_config.server)

    remote_path = project_config.remote_path
    data_dir = project_config.data_dir
    data_includes = project_config.data_includes

    excludes = get_excludes(project_root)
    exclude_lines = list(excludes) + data_includes

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

    try:
        run_rsync(rsync_cmd, verbose=verbose)
    finally:
        import os

        os.unlink(exclude_file)

    if data_dir and data_includes:
        typer.echo()
        typer.echo(f"Syncing {len(data_includes)} data items to {data_dir}")

        run_ssh_command(ssh_info, f"mkdir -p {shlex.quote(data_dir)}", verbose=verbose)

        data_options = ["--prune-empty-dirs", "--include=*/"]
        data_options.extend(f"--include={pattern}" for pattern in data_includes)
        data_options.append("--exclude=*")

        data_rsync_cmd = build_rsync_command(
            source=f"{project_root}/",
            destination=f"{ssh_info.user}@{ssh_info.hostname}:{data_dir}/",
            ssh_info=ssh_info,
            options=data_options,
        )

        run_rsync(data_rsync_cmd, verbose=verbose)

        symlink_parts = []
        for entry in data_includes:
            entry_name = entry.rstrip("/")
            symlink_parts.append(f"rm -rf {shlex.quote(f'{remote_path}/{entry_name}')}")
            symlink_parts.append(
                f"ln -s {shlex.quote(f'{data_dir}/{entry_name}')} {shlex.quote(f'{remote_path}/{entry_name}')}"
            )

        if symlink_parts:
            remote_command = " && ".join(symlink_parts)
            run_ssh_command(ssh_info, remote_command, verbose=verbose)
            typer.echo(f"Created {len(data_includes)} data symlinks")

    typer.echo()
    typer.echo("Sync completed successfully.")
