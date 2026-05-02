import typer
from mudsync.project import require_project
from mudsync.ssh_config import get_host_config
from mudsync.sync_rules import require_project_config


def command():
    project_root = require_project()
    project_config = require_project_config(project_root)
    ssh_info = get_host_config(project_config.server)

    items = [
        ("Host", ssh_info.host),
        ("IP", ssh_info.hostname),
        ("User", ssh_info.user),
        ("Port", str(ssh_info.port)),
        ("SSH Key", ssh_info.identity_file or "(not set)"),
        ("Remote Path", project_config.remote_path),
    ]
    label_width = max(len(label) for label, _ in items)
    for label, value in items:
        typer.echo(f"{label:>{label_width}}: {value}")