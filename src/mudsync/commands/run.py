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
from mudsync.project import require_project
from mudsync.ssh_config import get_host_config
from mudsync.sync_rules import require_project_config


def build_remote_up_command(
    remote_path: str,
    compose_file: str | None,
    service: str,
    build: bool,
    detach: bool,
) -> str:
    compose_args = build_compose_base_args(compose_file)
    up_args = [*compose_args, "up"]
    if build:
        up_args.append("--build")
    if detach:
        up_args.append("--detach")
    up_args.append(service)

    quoted = [shlex.quote(part) for part in up_args]
    command_parts = ["cd", shlex.quote(remote_path), "&&", *quoted]
    return " ".join(command_parts)


def build_remote_run_command(
    remote_path: str,
    compose_file: str | None,
    service: str,
    command_parts: list[str],
    no_rm: bool,
    detach: bool,
    name: str | None,
) -> str:
    compose_args = build_compose_base_args(compose_file)
    run_args = [*compose_args, "run", "--service-ports"]
    if not no_rm:
        run_args.append("--rm")
    if detach:
        run_args.append("--detach")
    if name:
        run_args.extend(["--name", name])
    run_args.append(service)
    run_args.extend(command_parts)

    quoted = [shlex.quote(part) for part in run_args]
    command_parts = ["cd", shlex.quote(remote_path), "&&", *quoted]
    return " ".join(command_parts)


def build_remote_build_then_run_command(
    remote_path: str,
    compose_file: str | None,
    service: str,
    command_parts: list[str],
    no_rm: bool,
    detach: bool,
    name: str | None,
) -> str:
    compose_args = build_compose_base_args(compose_file)
    build_args = [*compose_args, "build", service]
    run_args = [*compose_args, "run", "--service-ports"]
    if not no_rm:
        run_args.append("--rm")
    if detach:
        run_args.append("--detach")
    if name:
        run_args.extend(["--name", name])
    run_args.extend([service, *command_parts])

    quoted_build = [shlex.quote(part) for part in build_args]
    quoted_run = [shlex.quote(part) for part in run_args]
    command_parts = [
        "cd",
        shlex.quote(remote_path),
        "&&",
        *quoted_build,
        "&&",
        *quoted_run,
    ]
    return " ".join(command_parts)


def command(
    cmd: list[str] | None,
    service: str | None = None,
    build: bool = False,
    sync: bool = False,
    compose_file: str | None = None,
    no_rm: bool = False,
    detach: bool = False,
    name: str | None = None,
    verbose: bool = False,
):
    command_parts = list(cmd or [])

    project_root = require_project()
    project_config = require_project_config(project_root)
    ssh_info = get_host_config(project_config.server)

    remote_path = project_config.remote_path
    resolved_file = resolve_compose_file(project_root, compose_file)

    if sync:
        sync_cmd.command(verbose=verbose)

    resolved_service = resolve_service_name(
        ssh_info,
        remote_path,
        resolved_file,
        service,
    )

    if not command_parts:
        remote_cmd = build_remote_up_command(
            remote_path,
            resolved_file,
            resolved_service,
            build,
            detach,
        )
        ssh_cmd = build_ssh_command(ssh_info, remote_cmd)
        typer.echo(f"Starting on {ssh_info.hostname}: {resolved_service}")
    elif build:
        remote_cmd = build_remote_build_then_run_command(
            remote_path,
            resolved_file,
            resolved_service,
            command_parts,
            no_rm,
            detach,
            name,
        )
        ssh_cmd = build_ssh_command(ssh_info, remote_cmd)
        display_command = " ".join(shlex.quote(part) for part in command_parts)
        typer.echo(f"Running on {ssh_info.hostname}: {display_command}")
    else:
        remote_cmd = build_remote_run_command(
            remote_path,
            resolved_file,
            resolved_service,
            command_parts,
            no_rm,
            detach,
            name,
        )
        ssh_cmd = build_ssh_command(ssh_info, remote_cmd)
        display_command = " ".join(shlex.quote(part) for part in command_parts)
        typer.echo(f"Running on {ssh_info.hostname}: {display_command}")
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
