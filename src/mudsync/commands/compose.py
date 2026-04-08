import shlex
import subprocess
from pathlib import Path

from mudsync.ssh_config import SSHHost


def build_ssh_command(ssh_info: SSHHost, remote_command: str) -> list[str]:
    ssh_cmd = ["ssh"]
    if ssh_info.port != 22:
        ssh_cmd.extend(["-p", str(ssh_info.port)])
    if ssh_info.identity_file:
        ssh_cmd.extend(["-i", ssh_info.identity_file])
    ssh_cmd.append(f"{ssh_info.user}@{ssh_info.hostname}")
    ssh_cmd.append(remote_command)
    return ssh_cmd


def build_compose_base_args(compose_file: str | None) -> list[str]:
    compose_args = ["docker", "compose"]
    if compose_file:
        compose_args.extend(["--file", compose_file])
    return compose_args


def resolve_compose_file(project_root: Path, compose_file: str | None) -> str | None:
    if compose_file is None:
        return None

    fpath_compose = Path(compose_file)
    if not fpath_compose.exists():
        fpath_candidate = project_root / compose_file
        if not fpath_candidate.exists():
            raise SystemExit(f"Error: compose file not found: {compose_file}")
    return compose_file


def list_services(
    ssh_info: SSHHost,
    remote_path: str,
    compose_file: str | None,
) -> list[str]:
    compose_args = build_compose_base_args(compose_file)
    command_parts = [
        "cd",
        shlex.quote(remote_path),
        "&&",
        *[shlex.quote(part) for part in compose_args],
        "config",
        "--services",
    ]
    remote_command = " ".join(command_parts)
    ssh_cmd = build_ssh_command(ssh_info, remote_command)

    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit("Error: ssh command not found") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        detail = f"\nstderr: {stderr}" if stderr else ""
        raise SystemExit("Error: failed to resolve compose services." + detail) from exc

    services = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return services


def resolve_service_name(
    ssh_info: SSHHost,
    remote_path: str,
    compose_file: str | None,
    service: str | None,
) -> str:
    if service:
        return service

    services = list_services(ssh_info, remote_path, compose_file)
    if not services:
        raise SystemExit(
            "Error: no compose service found. Please specify --service explicitly."
        )
    return services[0]
