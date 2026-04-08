import typer

from mudsync.commands.sync import build_rsync_command, run_rsync
from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config


def build_filtered_transfer_options(patterns: list[str]) -> list[str]:
    options = ["--prune-empty-dirs", "--include=*/"]
    options.extend(f"--include={pattern}" for pattern in patterns)
    options.append("--exclude=*")
    return options


def command(patterns: list[str]) -> None:
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    remote_path = f"{app_config.remote_home}/{proj_name}"
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

    run_rsync(rsync_cmd)

    typer.echo()
    typer.echo("Push completed successfully.")
