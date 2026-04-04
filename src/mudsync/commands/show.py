import typer
from mudsync.config import require_config
from mudsync.ssh_config import get_host_config


def command():
    app_config = require_config()
    ssh_info = get_host_config(app_config.ssh_host)

    typer.echo(f"Host:        {ssh_info.host}")
    typer.echo(f"IP:          {ssh_info.hostname}")
    typer.echo(f"User:        {ssh_info.user}")
    typer.echo(f"Port:        {ssh_info.port}")
    typer.echo(f"SSH Key:     {ssh_info.identity_file or '(not set)'}")
    typer.echo(f"Remote Home: {app_config.remote_home}")
