import shlex
import subprocess

import typer

from mudsync.commands import sync as sync_cmd
from mudsync.commands.compose import (
    build_compose_base_args,
    build_ssh_command,
    resolve_compose_file,
    resolve_service_name,
)
from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config


def build_remote_run_command(
    remote_path: str,
    compose_file: str | None,
    service: str,
    command_parts: list[str],
    build: bool,
) -> str:
    compose_args = build_compose_base_args(compose_file)
    run_args = [*compose_args, "run", "--rm"]
    if build:
        run_args.append("--build")

    run_args.append(service)
    run_args.extend(command_parts)

    quoted = [shlex.quote(part) for part in run_args]
    command_parts = ["cd", shlex.quote(remote_path), "&&", *quoted]
    return " ".join(command_parts)


def command(
    cmd: list[str],
    service: str | None = None,
    build: bool = False,
    sync: bool = False,
    compose_file: str | None = None,
):
    if not cmd:
        raise SystemExit("Error: COMMAND is required")

    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    remote_path = f"{app_config.remote_home}/{proj_name}"
    resolved_file = resolve_compose_file(project_root, compose_file)

    if sync:
        sync_cmd.command()

    resolved_service = resolve_service_name(
        ssh_info,
        remote_path,
        resolved_file,
        service,
    )

    remote_cmd = build_remote_run_command(
        remote_path,
        resolved_file,
        resolved_service,
        cmd,
        build,
    )
    ssh_cmd = build_ssh_command(ssh_info, remote_cmd)

    display_command = " ".join(shlex.quote(part) for part in cmd)
    typer.echo(f"Running on {ssh_info.hostname}: {display_command}")
    typer.echo()

    try:
        result = subprocess.run(ssh_cmd, check=False)
    except FileNotFoundError as exc:
        raise SystemExit("Error: ssh command not found") from exc

    if result.returncode != 0:
        raise SystemExit(result.returncode)
