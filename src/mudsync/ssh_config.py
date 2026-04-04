import getpass
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import paramiko.config


@dataclass
class SSHHost:
    host: str
    hostname: str
    user: str
    port: int
    identity_file: Optional[str] = None


def _parse_ssh_config() -> paramiko.config.SSHConfig:
    ssh_config_path = Path.home() / ".ssh" / "config"
    if not ssh_config_path.exists():
        raise SystemExit(
            "Error: ~/.ssh/config not found.\n"
            "Please configure SSH access to your GPU server first."
        )
    ssh_config = paramiko.config.SSHConfig()
    with open(ssh_config_path) as f:
        ssh_config.parse(f)
    return ssh_config


def parse_ssh_config() -> dict[str, SSHHost]:
    ssh_config = _parse_ssh_config()
    hosts = {}
    for host in ssh_config.get_hostnames():
        if host == "*":
            continue
        config = ssh_config.lookup(host)
        hostname = config.get("hostname", host)
        user = config.get("user", getpass.getuser())
        port = int(config.get("port", 22))
        identity_file = config.get("identityfile", None)
        if identity_file and isinstance(identity_file, list):
            identity_file = str(Path(identity_file[0]).expanduser())
        elif identity_file:
            identity_file = str(Path(identity_file).expanduser())
        hosts[host] = SSHHost(
            host=host,
            hostname=hostname,
            user=user,
            port=port,
            identity_file=identity_file,
        )
    return hosts


def get_host_config(host: str) -> SSHHost:
    hosts = parse_ssh_config()
    if host not in hosts:
        raise ValueError(f"Host '{host}' not found in ~/.ssh/config")
    return hosts[host]


def list_hosts() -> list[str]:
    hosts = parse_ssh_config()
    return list(hosts.keys())
