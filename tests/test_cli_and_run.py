import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mudsync.cli import app
from mudsync.commands.run import (
    build_remote_build_then_run_command,
    build_remote_run_command,
    command,
)
from mudsync.ssh_config import SSHHost


class CLITestCase(unittest.TestCase):
    def test_build_command_removed(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["build"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such command 'build'", result.output)

    @patch("mudsync.cli.run_cmd.command")
    def test_run_accepts_multi_token_command(self, run_command_mock) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["run", "python", "eval.py", "--arg1", "val1"],
        )

        self.assertEqual(result.exit_code, 0)
        run_command_mock.assert_called_once_with(
            cmd=["python", "eval.py", "--arg1", "val1"],
            service=None,
            build=False,
            sync=False,
            compose_file=None,
        )

    @patch("mudsync.cli.run_cmd.command")
    def test_run_parses_build_before_command(self, run_command_mock) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["run", "--build", "nvidia-smi"],
        )

        self.assertEqual(result.exit_code, 0)
        run_command_mock.assert_called_once_with(
            cmd=["nvidia-smi"],
            service=None,
            build=True,
            sync=False,
            compose_file=None,
        )

    @patch("mudsync.cli.run_cmd.command")
    def test_run_parses_build_after_command(self, run_command_mock) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["run", "nvidia-smi", "--build"],
        )

        self.assertEqual(result.exit_code, 0)
        run_command_mock.assert_called_once_with(
            cmd=["nvidia-smi"],
            service=None,
            build=True,
            sync=False,
            compose_file=None,
        )


class RunCommandTestCase(unittest.TestCase):
    def test_build_remote_run_command(self) -> None:
        remote_cmd = build_remote_run_command(
            remote_path="/home/gpu/proj",
            compose_file="compose.yaml",
            service="worker",
            command_parts=["python", "main.py", "--epochs", "10"],
        )
        self.assertIn("cd /home/gpu/proj &&", remote_cmd)
        self.assertIn("docker compose --file compose.yaml run --rm", remote_cmd)
        self.assertNotIn(" run --rm --build", remote_cmd)
        self.assertIn("worker python main.py --epochs 10", remote_cmd)

    def test_build_remote_build_then_run_command(self) -> None:
        remote_cmd = build_remote_build_then_run_command(
            remote_path="/home/gpu/proj",
            compose_file="compose.yaml",
            service="worker",
            command_parts=["python", "main.py"],
        )
        self.assertIn("docker compose --file compose.yaml build worker", remote_cmd)
        self.assertIn(
            "&& docker compose --file compose.yaml run --rm worker", remote_cmd
        )

    def test_build_remote_run_command_without_file(self) -> None:
        remote_cmd = build_remote_run_command(
            remote_path="/home/gpu/proj",
            compose_file=None,
            service="worker",
            command_parts=["python", "main.py"],
        )
        self.assertIn("docker compose run --rm worker python main.py", remote_cmd)
        self.assertNotIn("--file", remote_cmd)

    @patch("mudsync.commands.run.subprocess.run")
    @patch("mudsync.commands.run.sync_cmd.command")
    @patch("mudsync.commands.run.resolve_service_name")
    @patch("mudsync.commands.run.resolve_compose_file")
    @patch("mudsync.commands.run.get_host_config")
    @patch("mudsync.commands.run.get_project_name")
    @patch("mudsync.commands.run.require_project")
    @patch("mudsync.commands.run.require_config")
    def test_command_runs_sync_and_ssh(
        self,
        require_config_mock,
        require_project_mock,
        get_project_name_mock,
        get_host_config_mock,
        resolve_compose_file_mock,
        resolve_service_name_mock,
        sync_mock,
        subprocess_run_mock,
    ) -> None:
        require_config_mock.return_value = SimpleNamespace(
            ssh_host="gpu",
            remote_home="/home/user",
        )
        require_project_mock.return_value = Path("/tmp/proj")
        get_project_name_mock.return_value = "proj"
        get_host_config_mock.return_value = SSHHost(
            host="gpu",
            hostname="gpu.example.com",
            user="ubuntu",
            port=22,
            identity_file=None,
        )
        resolve_compose_file_mock.return_value = None
        resolve_service_name_mock.return_value = "app"
        subprocess_run_mock.return_value = SimpleNamespace(returncode=0)

        command(
            cmd=["python", "app.py"],
            service=None,
            build=False,
            sync=True,
            compose_file=None,
        )

        sync_mock.assert_called_once()
        subprocess_run_mock.assert_called_once()
        ssh_cmd = subprocess_run_mock.call_args.args[0]
        self.assertEqual(ssh_cmd[0], "ssh")
        self.assertIn("ubuntu@gpu.example.com", ssh_cmd)
        self.assertIn("docker compose run --rm app python app.py", ssh_cmd[-1])
        self.assertNotIn("--file", ssh_cmd[-1])

    @patch("mudsync.commands.run.subprocess.run")
    @patch("mudsync.commands.run.resolve_service_name")
    @patch("mudsync.commands.run.resolve_compose_file")
    @patch("mudsync.commands.run.get_host_config")
    @patch("mudsync.commands.run.get_project_name")
    @patch("mudsync.commands.run.require_project")
    @patch("mudsync.commands.run.require_config")
    def test_build_option_runs_build_then_run(
        self,
        require_config_mock,
        require_project_mock,
        get_project_name_mock,
        get_host_config_mock,
        resolve_compose_file_mock,
        resolve_service_name_mock,
        subprocess_run_mock,
    ) -> None:
        require_config_mock.return_value = SimpleNamespace(
            ssh_host="gpu",
            remote_home="/home/user",
        )
        require_project_mock.return_value = Path("/tmp/proj")
        get_project_name_mock.return_value = "proj"
        get_host_config_mock.return_value = SSHHost(
            host="gpu",
            hostname="gpu.example.com",
            user="ubuntu",
            port=22,
            identity_file=None,
        )
        resolve_compose_file_mock.return_value = None
        resolve_service_name_mock.return_value = "app"
        subprocess_run_mock.return_value = SimpleNamespace(returncode=0)

        command(cmd=["python", "app.py"], build=True)

        ssh_cmd = subprocess_run_mock.call_args.args[0]
        self.assertIn("docker compose build app", ssh_cmd[-1])
        self.assertIn("&& docker compose run --rm app python app.py", ssh_cmd[-1])

    @patch("mudsync.commands.run.subprocess.run")
    @patch("mudsync.commands.run.sync_cmd.command")
    @patch("mudsync.commands.run.resolve_service_name")
    @patch("mudsync.commands.run.resolve_compose_file")
    @patch("mudsync.commands.run.get_host_config")
    @patch("mudsync.commands.run.get_project_name")
    @patch("mudsync.commands.run.require_project")
    @patch("mudsync.commands.run.require_config")
    def test_sync_runs_before_service_resolution(
        self,
        require_config_mock,
        require_project_mock,
        get_project_name_mock,
        get_host_config_mock,
        resolve_compose_file_mock,
        resolve_service_name_mock,
        sync_mock,
        subprocess_run_mock,
    ) -> None:
        call_order: list[str] = []

        require_config_mock.return_value = SimpleNamespace(
            ssh_host="gpu",
            remote_home="/home/user",
        )
        require_project_mock.return_value = Path("/tmp/proj")
        get_project_name_mock.return_value = "proj"
        get_host_config_mock.return_value = SSHHost(
            host="gpu",
            hostname="gpu.example.com",
            user="ubuntu",
            port=22,
            identity_file=None,
        )
        resolve_compose_file_mock.return_value = None
        resolve_service_name_mock.return_value = "app"
        subprocess_run_mock.return_value = SimpleNamespace(returncode=0)

        def sync_side_effect() -> None:
            call_order.append("sync")

        def resolve_service_side_effect(*args, **kwargs) -> str:
            call_order.append("resolve_service")
            return "app"

        sync_mock.side_effect = sync_side_effect
        resolve_service_name_mock.side_effect = resolve_service_side_effect

        command(
            cmd=["python", "app.py"],
            sync=True,
        )

        self.assertEqual(call_order[:2], ["sync", "resolve_service"])

    @patch("mudsync.commands.run.subprocess.run")
    @patch("mudsync.commands.run.resolve_service_name")
    @patch("mudsync.commands.run.resolve_compose_file")
    @patch("mudsync.commands.run.get_host_config")
    @patch("mudsync.commands.run.get_project_name")
    @patch("mudsync.commands.run.require_project")
    @patch("mudsync.commands.run.require_config")
    def test_command_propagates_remote_exit_code(
        self,
        require_config_mock,
        require_project_mock,
        get_project_name_mock,
        get_host_config_mock,
        resolve_compose_file_mock,
        resolve_service_name_mock,
        subprocess_run_mock,
    ) -> None:
        require_config_mock.return_value = SimpleNamespace(
            ssh_host="gpu",
            remote_home="/home/user",
        )
        require_project_mock.return_value = Path("/tmp/proj")
        get_project_name_mock.return_value = "proj"
        get_host_config_mock.return_value = SSHHost(
            host="gpu",
            hostname="gpu.example.com",
            user="ubuntu",
            port=22,
            identity_file=None,
        )
        resolve_compose_file_mock.return_value = None
        resolve_service_name_mock.return_value = "app"
        subprocess_run_mock.return_value = SimpleNamespace(returncode=12)

        with self.assertRaises(SystemExit) as ctx:
            command(cmd=["python", "app.py"])
        self.assertEqual(ctx.exception.code, 12)


if __name__ == "__main__":
    unittest.main()
