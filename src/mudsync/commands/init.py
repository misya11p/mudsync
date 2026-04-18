from pathlib import Path

import typer
from InquirerPy import inquirer

from mudsync.config import load_config
from mudsync.ssh_config import list_hosts
from mudsync.sync_rules import ProjectConfig, save_project_config


_CANCEL_KEYBINDINGS = {
    "skip": [{"key": "escape"}, {"key": "c-c"}],
    "interrupt": [{"key": "c-d"}],
}


def command():
    project_root = Path.cwd()
    project_name = project_root.name
    msync_json = project_root / "msync.json"

    if msync_json.exists():
        raise SystemExit(
            f"Error: msync.json already exists in {project_root}. "
            "Remove it first if you want to reinitialize."
        )

    global_config = load_config()
    if global_config is None:
        raise SystemExit("Error: Default config not set. Run 'msync default' first.")

    hosts = sorted(list_hosts())
    if not hosts:
        raise SystemExit("Error: No SSH hosts found in ~/.ssh/config")

    default_host = (
        global_config.ssh_host if global_config.ssh_host in hosts else hosts[0]
    )
    default_remote_path = f"{global_config.remote_path}/{project_name}"

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

    project_config = ProjectConfig(
        server=ssh_host,
        remote_path=remote_path,
        excludes=[],
    )
    save_project_config(project_root, project_config)

    typer.echo(f"Initialized msync.json: {ssh_host} -> {remote_path}")
