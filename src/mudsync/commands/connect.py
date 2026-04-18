import subprocess

from mudsync.project import require_project
from mudsync.ssh_config import get_host_config
from mudsync.sync_rules import require_project_config


def command():
    project_root = require_project()
    project_config = require_project_config(project_root)
    ssh_info = get_host_config(project_config.server)

    remote_path = project_config.remote_path

    ssh_cmd = [
        "ssh",
        "-t",
    ]

    if ssh_info.port != 22:
        ssh_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        ssh_cmd.extend(["-i", ssh_info.identity_file])

    ssh_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}")

    remote_cmd = f"mkdir -p {remote_path} && cd {remote_path} && exec $SHELL"
    ssh_cmd.append(remote_cmd)

    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Error: SSH connection failed with exit code {e.returncode}")
    except FileNotFoundError:
        raise SystemExit("Error: ssh command not found")
