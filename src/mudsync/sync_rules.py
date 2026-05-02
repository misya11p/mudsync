import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


DEFAULT_GLOBAL_EXCLUDES = [
    ".git/",
    "__pycache__/",
    ".venv/",
    "node_modules/",
    ".ipynb_checkpoints/",
    ".DS_Store",
    "*.pyc",
    "*.pyo",
]


@dataclass
class ProjectConfig:
    server: str
    remote_path: str
    excludes: list[str] = field(default_factory=list)
    data_dir: str | None = None
    data_includes: list[str] = field(default_factory=list)


def _msync_json_path(project_root: Path) -> Path:
    return project_root / "msync.json"


def load_project_config(project_root: Path) -> Optional[ProjectConfig]:
    path = _msync_json_path(project_root)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    data.setdefault("data_dir", None)
    data.setdefault("data_includes", [])
    return ProjectConfig(**data)


def save_project_config(project_root: Path, config: ProjectConfig) -> None:
    path = _msync_json_path(project_root)
    path.write_text(
        json.dumps(
            {
                "server": config.server,
                "remote_path": config.remote_path,
                "excludes": config.excludes,
                "data_dir": config.data_dir,
                "data_includes": config.data_includes,
            },
            indent=2,
        )
        + "\n"
    )


def require_project_config(project_root: Path) -> ProjectConfig:
    config = load_project_config(project_root)
    if config is None:
        raise SystemExit("Error: msync.json not found. Run 'msync set' first.")
    return config


def get_excludes(project_root: Path) -> list[str]:
    config = load_project_config(project_root)
    excludes = list(config.excludes) if config else []
    for pattern in DEFAULT_GLOBAL_EXCLUDES:
        if pattern not in excludes:
            excludes.append(pattern)
    return excludes
