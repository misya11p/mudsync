from pathlib import Path
from typing import Optional


def find_project_root(start: Optional[Path] = None) -> Path:
    if start is None:
        start = Path.cwd()

    current = start.resolve()
    while True:
        if (current / "msync.json").exists():
            return current

        parent = current.parent
        if parent == current:
            raise SystemExit(
                "Error: msync.json not found in current or parent directories.\n"
                "Run 'msync init' first."
            )
        current = parent


def require_project() -> Path:
    return find_project_root()
