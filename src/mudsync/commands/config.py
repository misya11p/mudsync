import typer
from InquirerPy import inquirer
from mudsync.config import AppConfig, save_config
from mudsync.ssh_config import list_hosts


def command():
    hosts = list_hosts()
    if not hosts:
        raise SystemExit("Error: No SSH hosts found in ~/.ssh/config")

    ssh_host = inquirer.select(
        message="Select SSH host:",
        choices=hosts,
    ).execute()

    remote_home = inquirer.text(
        message="Remote home directory:",
        default="/home",
    ).execute()

    config = AppConfig(ssh_host=ssh_host, remote_home=remote_home)
    save_config(config)

    typer.echo(f"Config saved: {ssh_host} -> {remote_home}")
