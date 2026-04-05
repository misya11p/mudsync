import typer
from mudsync.commands import config as config_cmd
from mudsync.commands import show as show_cmd
from mudsync.commands import connect as connect_cmd
from mudsync.commands import manage as manage_cmd
from mudsync.commands import sync as sync_cmd
from mudsync.commands import build as build_cmd
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
def show():
    """Show current SSH connection settings"""
    show_cmd.command()


@app.command()
def connect():
    """SSH connect to GPU server and cd to project directory"""
    connect_cmd.command()


@app.command()
def manage():
    """Manage files to sync (interactive)"""
    manage_cmd.command()


@app.command()
def sync():
    """Sync local project to GPU server via rsync"""
    sync_cmd.command()


@app.command()
def build():
    """Build Docker image on GPU server"""
    build_cmd.command()


@app.command()
def run(cmd: str | None = typer.Argument(None, help="Command to run in container")):
    """Run a command in Docker container on GPU server"""
    run_cmd.command(cmd)


@app.command()
def jupyter(port: int = typer.Option(8888, "--port", "-p", help="Local port number")):
    """Start Jupyter Lab on GPU server with port forwarding"""
    jupyter_cmd.command(port)


if __name__ == "__main__":
    app()
