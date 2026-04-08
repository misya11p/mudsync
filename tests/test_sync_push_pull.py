import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mudsync.commands import pull, push, sync
from mudsync.ssh_config import SSHHost


class _DummyTempFile:
    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def write(self, _value: str) -> int:
        return 0


class FilteredTransferTestCase(unittest.TestCase):
    def test_filtered_transfer_option_order(self) -> None:
        options = push.build_filtered_transfer_options(["models/*.pt", "logs/**"])
        self.assertEqual(
            options,
            [
                "--prune-empty-dirs",
                "--include=*/",
                "--include=models/*.pt",
                "--include=logs/**",
                "--exclude=*",
            ],
        )

    @patch("mudsync.commands.push.build_rsync_command")
    @patch("mudsync.commands.push.run_rsync")
    @patch("mudsync.commands.push.get_host_config")
    @patch("mudsync.commands.push.get_project_name")
    @patch("mudsync.commands.push.require_project")
    @patch("mudsync.commands.push.require_config")
    def test_push_uses_local_to_remote_direction(
        self,
        require_config_mock,
        require_project_mock,
        get_project_name_mock,
        get_host_config_mock,
        run_rsync_mock,
        build_rsync_command_mock,
    ) -> None:
        require_config_mock.return_value = SimpleNamespace(
            ssh_host="gpu", remote_home="/home/user"
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
        build_rsync_command_mock.return_value = ["rsync", "..."]

        push.command(["models/*.pt"])

        build_rsync_command_mock.assert_called_once_with(
            source="/tmp/proj/",
            destination="ubuntu@gpu.example.com:/home/user/proj/",
            ssh_info=get_host_config_mock.return_value,
            options=[
                "--prune-empty-dirs",
                "--include=*/",
                "--include=models/*.pt",
                "--exclude=*",
            ],
        )
        run_rsync_mock.assert_called_once_with(["rsync", "..."])

    @patch("mudsync.commands.pull.build_rsync_command")
    @patch("mudsync.commands.pull.run_rsync")
    @patch("mudsync.commands.pull.get_host_config")
    @patch("mudsync.commands.pull.get_project_name")
    @patch("mudsync.commands.pull.require_project")
    @patch("mudsync.commands.pull.require_config")
    def test_pull_uses_remote_to_local_direction(
        self,
        require_config_mock,
        require_project_mock,
        get_project_name_mock,
        get_host_config_mock,
        run_rsync_mock,
        build_rsync_command_mock,
    ) -> None:
        require_config_mock.return_value = SimpleNamespace(
            ssh_host="gpu", remote_home="/home/user"
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
        build_rsync_command_mock.return_value = ["rsync", "..."]

        pull.command(["outputs/*.csv"])

        build_rsync_command_mock.assert_called_once_with(
            source="ubuntu@gpu.example.com:/home/user/proj/",
            destination="/tmp/proj/",
            ssh_info=get_host_config_mock.return_value,
            options=[
                "--prune-empty-dirs",
                "--include=*/",
                "--include=outputs/*.csv",
                "--exclude=*",
            ],
        )
        run_rsync_mock.assert_called_once_with(["rsync", "..."])


class SyncRegressionTestCase(unittest.TestCase):
    @patch("os.unlink")
    @patch("mudsync.commands.sync.run_rsync")
    @patch("mudsync.commands.sync.get_excludes")
    @patch("mudsync.commands.sync.get_host_config")
    @patch("mudsync.commands.sync.get_project_name")
    @patch("mudsync.commands.sync.require_project")
    @patch("mudsync.commands.sync.require_config")
    @patch("mudsync.commands.sync.tempfile.NamedTemporaryFile")
    def test_sync_command_keeps_existing_rsync_flags(
        self,
        named_tempfile_mock,
        require_config_mock,
        require_project_mock,
        get_project_name_mock,
        get_host_config_mock,
        get_excludes_mock,
        run_rsync_mock,
        _unlink_mock,
    ) -> None:
        named_tempfile_mock.return_value = _DummyTempFile("/tmp/exclude_rules.txt")
        require_config_mock.return_value = SimpleNamespace(
            ssh_host="gpu",
            remote_home="/home/user",
            global_excludes=[],
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
        get_excludes_mock.return_value = [".git/", "node_modules/"]

        sync.command()

        rsync_cmd = run_rsync_mock.call_args.args[0]
        self.assertEqual(rsync_cmd[0:3], ["rsync", "-avz", "--delete"])
        self.assertEqual(rsync_cmd[3:5], ["--exclude-from", "/tmp/exclude_rules.txt"])
        self.assertEqual(rsync_cmd[-2], "/tmp/proj/")
        self.assertEqual(rsync_cmd[-1], "ubuntu@gpu.example.com:/home/user/proj/")


if __name__ == "__main__":
    unittest.main()
