import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import typer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mudsync.commands import config as config_cmd
from mudsync.config import AppConfig


class ConfigCommandTestCase(unittest.TestCase):
    @patch("mudsync.commands.config.save_config")
    @patch("mudsync.commands.config.load_config")
    @patch("mudsync.commands.config.list_hosts")
    @patch("mudsync.commands.config.inquirer")
    def test_uses_sorted_hosts_and_current_values_as_defaults(
        self,
        inquirer_mock,
        list_hosts_mock,
        load_config_mock,
        save_config_mock,
    ) -> None:
        list_hosts_mock.return_value = ["gpu-b", "gpu-a", "gpu-c"]
        load_config_mock.return_value = AppConfig(
            ssh_host="gpu-c",
            remote_home="/home/ubuntu",
            global_excludes=[".git/", "data/"],
        )

        select_prompt = Mock()
        select_prompt.execute.return_value = "gpu-a"
        text_prompt = Mock()
        text_prompt.execute.return_value = "/home/new"
        inquirer_mock.select.return_value = select_prompt
        inquirer_mock.text.return_value = text_prompt

        config_cmd.command()

        inquirer_mock.select.assert_called_once_with(
            message="Select SSH host:",
            choices=["gpu-a", "gpu-b", "gpu-c"],
            default="gpu-c",
            raise_keyboard_interrupt=False,
        )
        inquirer_mock.text.assert_called_once_with(
            message="Remote home directory:",
            default="/home/ubuntu",
            raise_keyboard_interrupt=False,
        )
        save_config_mock.assert_called_once_with(
            AppConfig(
                ssh_host="gpu-a",
                remote_home="/home/new",
                global_excludes=[".git/", "data/"],
            )
        )

    @patch("mudsync.commands.config.save_config")
    @patch("mudsync.commands.config.load_config")
    @patch("mudsync.commands.config.list_hosts")
    @patch("mudsync.commands.config.inquirer")
    def test_ctrl_c_cancellation_does_not_save(
        self,
        inquirer_mock,
        list_hosts_mock,
        load_config_mock,
        save_config_mock,
    ) -> None:
        list_hosts_mock.return_value = ["gpu-a"]
        load_config_mock.return_value = None

        select_prompt = Mock()
        select_prompt.execute.return_value = None
        inquirer_mock.select.return_value = select_prompt

        with self.assertRaises(typer.Exit) as ctx:
            config_cmd.command()

        self.assertEqual(ctx.exception.exit_code, 0)
        save_config_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
