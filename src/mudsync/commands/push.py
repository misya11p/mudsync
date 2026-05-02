import typer

from mudsync.commands.sync import build_rsync_command, run_rsync
from mudsync.project import require_project
from mudsync.ssh_config import get_host_config
from mudsync.sync_rules import require_project_config


def build_filtered_transfer_options(patterns: list[str]) -> list[str]:
    options = ["--prune-empty-dirs", "--include=*/"]
    options.extend(f"--include={pattern}" for pattern in patterns)
    options.append("--exclude=*")
    return options


def command(patterns: list[str], verbose: bool = False) -> None:
    project_root = require_project()
    project_config = require_project_config(project_root)
    ssh_info = get_host_config(project_config.server)

    remote_path = project_config.remote_path
    source = f"{project_root}/"
    destination = f"{ssh_info.user}@{ssh_info.hostname}:{remote_path}/"

    rsync_cmd = build_rsync_command(
        source=source,
        destination=destination,
        ssh_info=ssh_info,
        options=build_filtered_transfer_options(patterns),
    )

    typer.echo(f"Syncing(local->remote, filtered): {source} -> {destination}")
    typer.echo(f"Patterns: {len(patterns)}")
    typer.echo()

    run_rsync(rsync_cmd, verbose=verbose)

    typer.echo()
    typer.echo("Push completed successfully.")
