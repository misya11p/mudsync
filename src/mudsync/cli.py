import typer
from mudsync.commands import config as config_cmd
from mudsync.commands import show as show_cmd
from mudsync.commands import connect as connect_cmd
from mudsync.commands import manage as manage_cmd
from mudsync.commands import sync as sync_cmd
from mudsync.commands import push as push_cmd
from mudsync.commands import pull as pull_cmd
from mudsync.commands import run as run_cmd
from mudsync.commands import jupyter as jupyter_cmd


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
app = typer.Typer(
    help="MUDSync - GPU server synchronization CLI", context_settings=CONTEXT_SETTINGS
)


@app.command()
def config():
    """Configure GPU server connection settings"""
    config_cmd.command()


@app.command()
def info():
    """Show current SSH connection settings"""
    show_cmd.command()


@app.command()
def connect():
    """SSH connect to GPU server and cd to project directory"""
    connect_cmd.command()


@app.command()
def manage():
    """Manage exclude rules for sync command (interactive)"""
    manage_cmd.command()


@app.command()
def sync():
    """Sync local project to GPU server via rsync"""
    sync_cmd.command()


@app.command()
def push(
    patterns: list[str] = typer.Argument(
        ...,
        metavar="PATTERN [PATTERN ...]",
        help="Glob patterns to transfer from local to remote",
    ),
):
    """Push filtered files from local project to GPU server"""
    push_cmd.command(patterns)


@app.command()
def pull(
    patterns: list[str] = typer.Argument(
        ...,
        metavar="PATTERN [PATTERN ...]",
        help="Glob patterns to transfer from remote to local",
    ),
):
    """Pull filtered files from GPU server to local project"""
    pull_cmd.command(patterns)


@app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    }
)
def run(
    ctx: typer.Context,
    cmd: list[str] | None = typer.Argument(
        None,
        metavar="COMMAND [ARGS]...",
        help="Command and arguments to run",
    ),
    service: str | None = typer.Option(
        None,
        "--service",
        "-s",
        help="Compose service name",
    ),
    build: bool = typer.Option(
        False,
        "--build",
        "-b",
        help="Build images before run",
    ),
    sync: bool = typer.Option(
        False,
        "--sync",
        "-y",
        help="Run sync before command",
    ),
    compose_file: str | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Compose file path",
    ),
    no_rm: bool = typer.Option(
        False,
        "--no-rm",
        help="Do not remove container after run",
    ),
    detach: bool = typer.Option(
        False,
        "--detach",
        "-d",
        help="Run container in background",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Assign a container name",
    ),
):
    """Run a command in a compose service on GPU server"""
    command_parts = [*(cmd or []), *ctx.args]
    run_cmd.command(
        cmd=command_parts,
        service=service,
        build=build,
        sync=sync,
        compose_file=compose_file,
        no_rm=no_rm,
        detach=detach,
        name=name,
    )


@app.command()
def jupyter(
    port: int = typer.Option(8888, "--port", "-p", help="Local port number"),
    service: str | None = typer.Option(
        None,
        "--service",
        "-s",
        help="Compose service name",
    ),
    build: bool = typer.Option(
        False,
        "--build",
        "-b",
        help="Build images before startup",
    ),
    sync: bool = typer.Option(
        False,
        "--sync",
        "-y",
        help="Run sync before startup",
    ),
    compose_file: str | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Compose file path",
    ),
):
    """Start Jupyter service with docker compose"""
    jupyter_cmd.command(
        port=port,
        service=service,
        build=build,
        sync=sync,
        compose_file=compose_file,
    )


if __name__ == "__main__":
    app()
