import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SyncRules:
    project_path: str
    excludes: list[str] = field(default_factory=list)


def get_state_dir() -> Path:
    state_home = Path(
        os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")
    )
    return state_home / "mudsync" / "sync_rules"


def project_hash(project_path: Path) -> str:
    return hashlib.sha256(str(project_path.resolve()).encode()).hexdigest()[:16]


def load_rules(project_root: Path) -> SyncRules:
    state_path = get_state_dir() / f"{project_hash(project_root)}.json"
    if not state_path.exists():
        return SyncRules(project_path=str(project_root.resolve()))
    data = json.loads(state_path.read_text())
    return SyncRules(**data)


def save_rules(rules: SyncRules) -> None:
    state_path = get_state_dir() / f"{project_hash(Path(rules.project_path))}.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "project_path": rules.project_path,
                "excludes": rules.excludes,
            },
            indent=2,
        )
    )


def get_excludes(
    project_root: Path, global_excludes: list[str] | None = None
) -> list[str]:
    rules = load_rules(project_root)
    excludes = list(rules.excludes)
    if global_excludes:
        for pattern in global_excludes:
            if pattern not in excludes:
                excludes.append(pattern)
    return excludes
