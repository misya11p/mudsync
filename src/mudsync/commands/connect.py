import os
import subprocess
import sys

import typer

from mudsync.config import require_config
from mudsync.project import get_project_name, require_project
from mudsync.ssh_config import get_host_config


def command():
    app_config = require_config()
    project_root = require_project()
    proj_name = get_project_name(project_root)
    ssh_info = get_host_config(app_config.ssh_host)

    remote_path = f"{app_config.remote_home}/{proj_name}"

    ssh_cmd = [
        "ssh",
        "-t",
    ]

    if ssh_info.port != 22:
        ssh_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        ssh_cmd.extend(["-i", ssh_info.identity_file])

    ssh_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}")

    remote_cmd = f"cd {remote_path} && exec $SHELL"
    ssh_cmd.append(remote_cmd)

    try:
        os.execvp(ssh_cmd[0], ssh_cmd)
    except OSError as e:
        raise SystemExit(f"Error: Failed to execute SSH: {e}")
