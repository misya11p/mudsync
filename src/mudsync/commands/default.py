import typer
from InquirerPy import inquirer
from mudsync.config import AppConfig, load_config, save_config
from mudsync.ssh_config import list_hosts


_CANCEL_KEYBINDINGS = {
    "skip": [{"key": "escape"}, {"key": "c-c"}],
    "interrupt": [{"key": "c-d"}],
}


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
    default_remote_path = current_config.remote_path if current_config else "/home"
    default_data_dir = current_config.data_dir if current_config else None

    ssh_host = inquirer.select(
        message="Select SSH host:",
        choices=hosts,
        default=default_host,
        mandatory=False,
        keybindings=_CANCEL_KEYBINDINGS,
        raise_keyboard_interrupt=False,
    ).execute()
    if ssh_host is None:
        typer.echo("Config cancelled.")
        raise typer.Exit(code=0)

    remote_path = inquirer.text(
        message="Remote path:",
        default=default_remote_path,
        mandatory=False,
        keybindings=_CANCEL_KEYBINDINGS,
        raise_keyboard_interrupt=False,
    ).execute()
    if remote_path is None:
        typer.echo("Config cancelled.")
        raise typer.Exit(code=0)

    data_dir = inquirer.text(
        message="Data directory path (remote, optional):",
        default=default_data_dir or "",
        mandatory=False,
        keybindings=_CANCEL_KEYBINDINGS,
        raise_keyboard_interrupt=False,
    ).execute()
    data_dir = data_dir.strip() or None

    config = AppConfig(
        ssh_host=ssh_host,
        remote_path=remote_path,
        data_dir=data_dir,
    )
    save_config(config)

    typer.echo(f"Default config saved: {ssh_host} -> {remote_path}")
    if data_dir:
        typer.echo(f"  Data directory: {data_dir}")
