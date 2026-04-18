import typer

from mudsync.commands.push import build_filtered_transfer_options
from mudsync.commands.sync import build_rsync_command, run_rsync
from mudsync.project import require_project
from mudsync.ssh_config import get_host_config
from mudsync.sync_rules import require_project_config


def command(patterns: list[str]) -> None:
    project_root = require_project()
    project_config = require_project_config(project_root)
    ssh_info = get_host_config(project_config.server)

    data_includes = project_config.data_includes
    conflicting = [
        p for p in patterns if p in data_includes or p.rstrip("/") in data_includes
    ]
    if conflicting:
        raise SystemExit(
            f"Error: Cannot pull data directory items via symlink: {', '.join(conflicting)}\n"
            "Data directory items are stored as symlinks on the remote and cannot be pulled."
        )

    remote_path = project_config.remote_path
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
