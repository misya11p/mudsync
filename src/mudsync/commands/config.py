import typer
from InquirerPy import inquirer
from mudsync.config import AppConfig, DEFAULT_GLOBAL_EXCLUDES, load_config, save_config
from mudsync.ssh_config import list_hosts


def command():
    hosts = sorted(list_hosts())
    if not hosts:
        raise SystemExit("Error: No SSH hosts found in ~/.ssh/config")

    current_config = load_config()
    default_host = (
        current_config.ssh_host
        if current_config and current_config.ssh_host in hosts
        else hosts[0]
    )
    default_remote_home = current_config.remote_home if current_config else "/home"

    ssh_host = inquirer.select(
        message="Select SSH host:",
        choices=hosts,
        default=default_host,
        raise_keyboard_interrupt=False,
    ).execute()
    if ssh_host is None:
        typer.echo("Config cancelled.")
        raise typer.Exit(code=0)

    remote_home = inquirer.text(
        message="Remote home directory:",
        default=default_remote_home,
        raise_keyboard_interrupt=False,
    ).execute()
    if remote_home is None:
        typer.echo("Config cancelled.")
        raise typer.Exit(code=0)

    config = AppConfig(
        ssh_host=ssh_host,
        remote_home=remote_home,
        global_excludes=(
            list(current_config.global_excludes)
            if current_config
            else list(DEFAULT_GLOBAL_EXCLUDES)
        ),
    )
    save_config(config)

    typer.echo(f"Config saved: {ssh_host} -> {remote_home}")
