from __future__ import annotations

import re
import shlex
import subprocess
from urllib.parse import urlparse, urlunparse

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
from mudsync.ssh_config import SSHHost, get_host_config

JUPYTER_URL_PATTERN = re.compile(r"https?://[^\s]*token=[^\s]+")


def build_remote_up_command(
    remote_path: str,
    compose_file: str | None,
    service: str,
    build: bool,
) -> str:
    compose_args = build_compose_base_args(compose_file)
    up_args = [*compose_args, "up"]
    if build:
        up_args.append("--build")
    up_args.append(service)

    quoted = [shlex.quote(part) for part in up_args]
    command_parts = ["cd", shlex.quote(remote_path), "&&", *quoted]
    return " ".join(command_parts)


def build_remote_down_command(
    remote_path: str,
    compose_file: str | None,
) -> str:
    compose_args = build_compose_base_args(compose_file)
    down_args = [*compose_args, "down"]
    quoted = [shlex.quote(part) for part in down_args]
    command_parts = ["cd", shlex.quote(remote_path), "&&", *quoted]
    return " ".join(command_parts)


def replace_url_host_port(url: str, ssh_info: SSHHost, port: int) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url

    rewritten = parsed._replace(netloc=f"{ssh_info.hostname}:{port}")
    return urlunparse(rewritten)


def extract_jupyter_url(log_line: str) -> str | None:
    match = JUPYTER_URL_PATTERN.search(log_line)
    if not match:
        return None
    return match.group(0)


def _run_compose_down(
    ssh_info: SSHHost,
    remote_path: str,
    compose_file: str | None,
) -> None:
    down_cmd = build_remote_down_command(remote_path, compose_file)
    ssh_cmd = build_ssh_command(ssh_info, down_cmd)
    subprocess.run(ssh_cmd, check=False)


def command(
    port: int = 8888,
    service: str | None = None,
    build: bool = False,
    sync: bool = False,
    compose_file: str | None = None,
) -> None:
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    remote_path = f"{app_config.remote_home}/{proj_name}"
    resolved_file = resolve_compose_file(project_root, compose_file)
    resolved_service = resolve_service_name(
        ssh_info,
        remote_path,
        resolved_file,
        service,
    )

    if sync:
        sync_cmd.command()

    up_cmd = build_remote_up_command(
        remote_path,
        resolved_file,
        resolved_service,
        build,
    )
    ssh_cmd = build_ssh_command(ssh_info, up_cmd)

    typer.echo(f"Starting Jupyter service on {ssh_info.hostname}...")
    typer.echo("Press Ctrl+C to stop and run compose down.")
    typer.echo()

    displayed_url = False
    process = subprocess.Popen(
        ssh_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        assert process.stdout is not None
        for line in process.stdout:
            typer.echo(line, nl=False)
            if displayed_url:
                continue
            detected_url = extract_jupyter_url(line)
            if not detected_url:
                continue

            rewritten = replace_url_host_port(detected_url, ssh_info, port)
            typer.echo()
            typer.echo(f"Jupyter Lab URL: {rewritten}")
            typer.echo()
            displayed_url = True
    except KeyboardInterrupt:
        typer.echo("\nStopping Jupyter service...")
        process.terminate()
        process.wait(timeout=10)
        _run_compose_down(ssh_info, remote_path, resolved_file)
        return
    except FileNotFoundError as exc:
        raise SystemExit("Error: ssh command not found") from exc

    return_code = process.wait()
    if return_code != 0:
        raise SystemExit(return_code)

    if not displayed_url:
        typer.echo()
        typer.echo(
            "Note: Could not auto-detect Jupyter URL from logs. "
            "Check output above for the token URL."
        )
