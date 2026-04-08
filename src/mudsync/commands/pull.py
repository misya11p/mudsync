import typer

from mudsync.commands.push import build_filtered_transfer_options
from mudsync.commands.sync import build_rsync_command, run_rsync
from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config


def command(patterns: list[str]) -> None:
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    remote_path = f"{app_config.remote_home}/{proj_name}"
    source = f"{ssh_info.user}@{ssh_info.hostname}:{remote_path}/"
    destination = f"{project_root}/"

    rsync_cmd = build_rsync_command(
        source=source,
        destination=destination,
        ssh_info=ssh_info,
        options=build_filtered_transfer_options(patterns),
    )

    typer.echo(f"Syncing(remote->local, filtered): {source} -> {destination}")
    typer.echo(f"Patterns: {len(patterns)}")
    typer.echo()

    run_rsync(rsync_cmd)

    typer.echo()
    typer.echo("Pull completed successfully.")
