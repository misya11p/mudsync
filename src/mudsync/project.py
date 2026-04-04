from pathlib import Path
from typing import Optional


def find_project_root(start: Optional[Path] = None) -> Path:
    if start is None:
        start = Path.cwd()

    current = start.resolve()
    while True:
        if (current / ".git").exists():
            return current

        parent = current.parent
        if parent == current:
            raise SystemExit(
                "Error: Not a git repository (or any of the parent directories).\n"
                "Run this command from within a git project."
            )
        current = parent


def get_project_name(project_root: Path) -> str:
    return project_root.name


def require_project() -> Path:
    return find_project_root()
