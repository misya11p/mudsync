from pathlib import Path

import typer
from InquirerPy import inquirer

from mudsync.config import load_config
from mudsync.ssh_config import list_hosts
from mudsync.sync_rules import ProjectConfig, load_project_config, save_project_config


_CANCEL_KEYBINDINGS = {
    "skip": [{"key": "escape"}, {"key": "c-c"}],
    "interrupt": [{"key": "c-d"}],
}


def command():
    project_root = Path.cwd()
    project_name = project_root.name
    msync_json = project_root / "msync.json"

    existing_config = load_project_config(project_root)

    global_config = load_config()
    if global_config is None:
        raise SystemExit("Error: Default config not set. Run 'msync default' first.")

    hosts = sorted(list_hosts())
    if not hosts:
        raise SystemExit("Error: No SSH hosts found in ~/.ssh/config")

    default_host = (
        existing_config.server
        if existing_config and existing_config.server in hosts
        else (global_config.ssh_host if global_config.ssh_host in hosts else hosts[0])
    )
    default_remote_path = (
        existing_config.remote_path
        if existing_config
        else f"{global_config.remote_path}/{project_name}"
    )
    default_data_dir = (
        existing_config.data_dir
        if existing_config and existing_config.data_dir
        else (
            f"{global_config.data_dir}/{project_name}" if global_config.data_dir else ""
        )
    )

    ssh_host = inquirer.select(
        message="Select SSH host:",
        choices=hosts,
        default=default_host,
        mandatory=False,
        keybindings=_CANCEL_KEYBINDINGS,
        raise_keyboard_interrupt=False,
    ).execute()
    if ssh_host is None:
        typer.echo("Init cancelled.")
        raise typer.Exit(code=0)

    remote_path = inquirer.text(
        message="Remote path:",
        default=default_remote_path,
        mandatory=False,
        keybindings=_CANCEL_KEYBINDINGS,
        raise_keyboard_interrupt=False,
    ).execute()
    if remote_path is None:
        typer.echo("Init cancelled.")
        raise typer.Exit(code=0)

    data_dir = inquirer.text(
        message="Data directory path (remote, optional):",
        default=default_data_dir,
        mandatory=False,
        keybindings=_CANCEL_KEYBINDINGS,
        raise_keyboard_interrupt=False,
    ).execute()
    data_dir = data_dir.strip() or None if data_dir else None

    existing_excludes = existing_config.excludes if existing_config else []
    existing_data_includes = existing_config.data_includes if existing_config else []

    project_config = ProjectConfig(
        server=ssh_host,
        remote_path=remote_path,
        excludes=existing_excludes,
        data_dir=data_dir,
        data_includes=existing_data_includes,
    )
    save_project_config(project_root, project_config)

    typer.echo(f"Initialized msync.json: {ssh_host} -> {remote_path}")
    if data_dir:
        typer.echo(f"  Data directory: {data_dir}")
