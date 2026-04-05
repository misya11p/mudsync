import subprocess

import typer

from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config
from mudsync.sync_rules import get_excludes


def command():
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    remote_path = f"{app_config.remote_home}/{proj_name}"

    rsync_cmd = [
        "rsync",
        "-avz",
        "--delete-excluded",
        "--exclude",
        ".git/",
    ]

    excludes = get_excludes(project_root)
    for exclude in excludes:
        if exclude == ".git" or exclude == ".git/":
            continue
        rsync_cmd.extend(["--exclude", exclude])

    ssh_opts = "-o StrictHostKeyChecking=no"
    if ssh_info.port != 22:
        ssh_opts += f" -p {ssh_info.port}"
    if ssh_info.identity_file:
        ssh_opts += f" -i {ssh_info.identity_file}"

    rsync_cmd.extend(["-e", f"ssh {ssh_opts}"])

    rsync_cmd.append(f"{project_root}/")
    rsync_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}:{remote_path}/")

    typer.echo(
        f"Syncing {project_root} -> {ssh_info.user}@{ssh_info.hostname}:{remote_path}/"
    )
    typer.echo(f"Excludes: {len(excludes) + 1} rules (including .git/)")
    typer.echo()

    try:
        result = subprocess.run(rsync_cmd, check=True)
        typer.echo()
        typer.echo("Sync completed successfully.")
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Error: rsync failed with exit code {e.returncode}")
    except FileNotFoundError:
        raise SystemExit(
            "Error: rsync not found. Please install rsync:\n"
            "  macOS: brew install rsync\n"
            "  Ubuntu: sudo apt install rsync"
        )
