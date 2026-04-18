import typer
from mudsync.project import require_project
from mudsync.ssh_config import get_host_config
from mudsync.sync_rules import require_project_config


def command():
    project_root = require_project()
    project_config = require_project_config(project_root)
    ssh_info = get_host_config(project_config.server)

    typer.echo(f"Host:        {ssh_info.host}")
    typer.echo(f"IP:          {ssh_info.hostname}")
    typer.echo(f"User:        {ssh_info.user}")
    typer.echo(f"Port:        {ssh_info.port}")
    typer.echo(f"SSH Key:     {ssh_info.identity_file or '(not set)'}")
    typer.echo(f"Remote Path: {project_config.remote_path}")
