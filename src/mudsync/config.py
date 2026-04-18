import os
from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    ssh_host: str
    remote_path: str


def get_config_dir() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "mudsync"


def load_config() -> Optional[AppConfig]:
    config_path = get_config_dir() / "config.json"
    if not config_path.exists():
        return None
    data = json.loads(config_path.read_text())
    if "remote_home" in data:
        data["remote_path"] = data.pop("remote_home")
    if "global_excludes" in data:
        del data["global_excludes"]
    return AppConfig(**data)


def save_config(config: AppConfig) -> None:
    config_path = get_config_dir() / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(asdict(config), indent=2))


def require_config() -> AppConfig:
    config = load_config()
    if config is None:
        raise SystemExit("Error: Default config not set. Run 'msync default' first.")
    return config
