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

    def test_push_and_pull_commands_exist(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("push", result.output)
        self.assertIn("pull", result.output)

    @patch("mudsync.cli.push_cmd.command")
    def test_push_forwards_patterns(self, push_command_mock) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["push", "models/*.pt", "logs/**/*.json"])
        self.assertEqual(result.exit_code, 0)
        push_command_mock.assert_called_once_with(["models/*.pt", "logs/**/*.json"])

    @patch("mudsync.cli.pull_cmd.command")
    def test_pull_forwards_patterns(self, pull_command_mock) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["pull", "outputs/*.csv"])
        self.assertEqual(result.exit_code, 0)
        pull_command_mock.assert_called_once_with(["outputs/*.csv"])

    def test_push_requires_pattern_argument(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["push"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Missing argument", result.output)

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
            no_rm=False,
            detach=False,
            name=None,
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
            no_rm=False,
            detach=False,
            name=None,
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
            no_rm=False,
            detach=False,
            name=None,
        )

    @patch("mudsync.cli.run_cmd.command")
    def test_run_parses_run_control_options(self, run_command_mock) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--no-rm",
                "--detach",
                "--name",
                "train-run-01",
                "python",
                "train.py",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        run_command_mock.assert_called_once_with(
            cmd=["python", "train.py"],
            service=None,
            build=False,
            sync=False,
            compose_file=None,
            no_rm=True,
            detach=True,
            name="train-run-01",
        )

    @patch("mudsync.cli.run_cmd.command")
    def test_run_allows_omitting_command(self, run_command_mock) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["run", "--service", "worker"],
        )

        self.assertEqual(result.exit_code, 0)
        run_command_mock.assert_called_once_with(
            cmd=[],
            service="worker",
            build=False,
            sync=False,
            compose_file=None,
            no_rm=False,
            detach=False,
            name=None,
        )


class RunCommandTestCase(unittest.TestCase):
    def test_build_remote_run_command(self) -> None:
        remote_cmd = build_remote_run_command(
            remote_path="/home/gpu/proj",
            compose_file="compose.yaml",
            service="worker",
            command_parts=["python", "main.py", "--epochs", "10"],
            no_rm=False,
            detach=False,
            name=None,
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
            no_rm=False,
            detach=False,
            name=None,
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
            no_rm=False,
            detach=False,
            name=None,
        )
        self.assertIn("docker compose run --rm worker python main.py", remote_cmd)
        self.assertNotIn("--file", remote_cmd)

    def test_build_remote_run_command_with_no_rm_detach_and_name(self) -> None:
        remote_cmd = build_remote_run_command(
            remote_path="/home/gpu/proj",
            compose_file=None,
            service="worker",
            command_parts=["python", "main.py"],
            no_rm=True,
            detach=True,
            name="custom-run",
        )
        self.assertIn("docker compose run --detach --name custom-run", remote_cmd)
        self.assertNotIn(" --rm ", remote_cmd)

    def test_build_remote_run_command_without_explicit_command(self) -> None:
        remote_cmd = build_remote_run_command(
            remote_path="/home/gpu/proj",
            compose_file=None,
            service="worker",
            command_parts=[],
            no_rm=False,
            detach=False,
            name=None,
        )
        self.assertIn("docker compose run --rm worker", remote_cmd)
        self.assertNotIn("worker python", remote_cmd)

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
            no_rm=False,
            detach=False,
            name=None,
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
    @patch("mudsync.commands.run.resolve_service_name")
    @patch("mudsync.commands.run.resolve_compose_file")
    @patch("mudsync.commands.run.get_host_config")
    @patch("mudsync.commands.run.get_project_name")
    @patch("mudsync.commands.run.require_project")
    @patch("mudsync.commands.run.require_config")
    def test_command_applies_no_rm_detach_and_name(
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

        command(
            cmd=["python", "app.py"],
            no_rm=True,
            detach=True,
            name="run-test",
        )

        ssh_cmd = subprocess_run_mock.call_args.args[0]
        self.assertIn(
            "docker compose run --detach --name run-test app python app.py", ssh_cmd[-1]
        )
        self.assertNotIn(" --rm ", ssh_cmd[-1])

    @patch("mudsync.commands.run.subprocess.run")
    @patch("mudsync.commands.run.resolve_service_name")
    @patch("mudsync.commands.run.resolve_compose_file")
    @patch("mudsync.commands.run.get_host_config")
    @patch("mudsync.commands.run.get_project_name")
    @patch("mudsync.commands.run.require_project")
    @patch("mudsync.commands.run.require_config")
    def test_command_runs_service_default_command_when_cmd_omitted(
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

        command(cmd=[])

        ssh_cmd = subprocess_run_mock.call_args.args[0]
        self.assertIn("docker compose run --rm app", ssh_cmd[-1])

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
