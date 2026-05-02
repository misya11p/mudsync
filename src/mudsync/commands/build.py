import shlex
import subprocess

import typer

from mudsync.commands.compose import (
    build_compose_base_args,
    build_ssh_command,
    resolve_compose_file,
)
from mudsync.project import require_project
from mudsync.sync_rules import require_project_config
from mudsync.ssh_config import get_host_config


def build_remote_build_command(
    remote_path: str,
    compose_file: str | None,
    service: str | None,
) -> str:
    compose_args = build_compose_base_args(compose_file)
    build_args = [*compose_args, "build"]
    if service:
        build_args.append(service)
    quoted = [shlex.quote(part) for part in build_args]
    command_parts = ["cd", shlex.quote(remote_path), "&&", *quoted]
    return " ".join(command_parts)


def command(
    service: str | None = None,
    compose_file: str | None = None,
    verbose: bool = False,
):
    project_root = require_project()
    project_config = require_project_config(project_root)
    ssh_info = get_host_config(project_config.server)

    remote_path = project_config.remote_path
    resolved_file = resolve_compose_file(project_root, compose_file)

    remote_cmd = build_remote_build_command(
        remote_path,
        resolved_file,
        service,
    )
    ssh_cmd = build_ssh_command(ssh_info, remote_cmd)

    target = service or "(all services)"
    typer.echo(f"Building on {ssh_info.hostname}: {target}")
    typer.echo()

    if verbose:
        typer.echo(f"$ {shlex.join(ssh_cmd)}")
        typer.echo()

    try:
        result = subprocess.run(ssh_cmd, check=False)
    except FileNotFoundError as exc:
        raise SystemExit("Error: ssh command not found") from exc

    if result.returncode != 0:
        raise SystemExit(result.returncode)
