import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mudsync.commands.jupyter import (
    build_remote_down_command,
    build_remote_up_command,
    command,
    extract_jupyter_url,
    replace_url_host_port,
)
from mudsync.ssh_config import SSHHost


class _InterruptingStream:
    def __iter__(self):
        return self

    def __next__(self):
        raise KeyboardInterrupt


class JupyterHelpersTestCase(unittest.TestCase):
    def test_extract_jupyter_url(self) -> None:
        line = "http://127.0.0.1:8888/lab?token=abcdef123"
        self.assertEqual(extract_jupyter_url(line), line)

    def test_replace_url_host_port(self) -> None:
        ssh_info = SSHHost(
            host="gpu",
            hostname="gpu.example.com",
            user="ubuntu",
            port=22,
            identity_file=None,
        )
        rewritten = replace_url_host_port(
            "http://127.0.0.1:8888/lab?token=abc",
            ssh_info,
            9999,
        )
        self.assertEqual(
            rewritten,
            "http://gpu.example.com:9999/lab?token=abc",
        )

    def test_build_remote_up_and_down_command(self) -> None:
        up_cmd = build_remote_up_command(
            "/remote/proj", "compose.yaml", "notebook", True
        )
        down_cmd = build_remote_down_command("/remote/proj", "compose.yaml")
        self.assertIn("docker compose --file compose.yaml up --build notebook", up_cmd)
        self.assertIn("docker compose --file compose.yaml down", down_cmd)

    def test_build_remote_up_and_down_command_without_file(self) -> None:
        up_cmd = build_remote_up_command("/remote/proj", None, "notebook", False)
        down_cmd = build_remote_down_command("/remote/proj", None)
        self.assertIn("docker compose up notebook", up_cmd)
        self.assertNotIn("--file", up_cmd)
        self.assertIn("docker compose down", down_cmd)
        self.assertNotIn("--file", down_cmd)


class JupyterCommandTestCase(unittest.TestCase):
    @patch("mudsync.commands.jupyter._run_compose_down")
    @patch("mudsync.commands.jupyter.subprocess.Popen")
    @patch("mudsync.commands.jupyter.resolve_service_name")
    @patch("mudsync.commands.jupyter.resolve_compose_file")
    @patch("mudsync.commands.jupyter.get_host_config")
    @patch("mudsync.commands.jupyter.get_project_name")
    @patch("mudsync.commands.jupyter.require_project")
    @patch("mudsync.commands.jupyter.require_config")
    def test_keyboard_interrupt_runs_compose_down(
        self,
        require_config_mock,
        require_project_mock,
        get_project_name_mock,
        get_host_config_mock,
        resolve_compose_file_mock,
        resolve_service_name_mock,
        popen_mock,
        run_compose_down_mock,
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
        resolve_service_name_mock.return_value = "notebook"

        process_mock = Mock()
        process_mock.stdout = _InterruptingStream()
        process_mock.wait.return_value = 0
        popen_mock.return_value = process_mock

        command(port=8888)

        process_mock.terminate.assert_called_once()
        run_compose_down_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
