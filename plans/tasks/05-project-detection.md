# Task 5: プロジェクト検出

## 概要

カレントディレクトリから上位へ辿り、`.git` ディレクトリが存在する場所をプロジェクトルートとして検出するモジュールを実装する。project系コマンドの共通基盤。

## 実施内容

### 5.1 ファイル: `src/mudsync/project.py`

```python
import os
from pathlib import Path
from typing import Optional


def find_project_root(start: Optional[Path] = None) -> Path:
    """
    カレントディレクトリから上位へ辿り、.gitがある場所をプロジェクトルートとして返す。

    Args:
        start: 検索開始ディレクトリ（デフォルト: カレントディレクトリ）

    Returns:
        Path: プロジェクトルートのパス

    Raises:
        SystemExit: .gitが見つからない場合
    """
    if start is None:
        start = Path.cwd()

    current = start.resolve()
    while True:
        if (current / ".git").exists():
            return current

        parent = current.parent
        if parent == current:
            # ルートに到達
            raise SystemExit(
                "Error: Not a git repository (or any of the parent directories).\n"
                "Run this command from within a git project."
            )
        current = parent


def get_project_name(project_root: Path) -> str:
    """
    プロジェクトルートディレクトリ名を返す。

    Args:
        project_root: プロジェクトルートのパス

    Returns:
        str: ディレクトリ名（例: /home/user/my-project -> my-project）
    """
    return project_root.name


def require_project() -> Path:
    """
    プロジェクトルートを検出し、存在を保証する。

    Returns:
        Path: プロジェクトルートのパス

    Side Effects:
        プロジェクトが見つからない場合はエラーメッセージを表示して終了
    """
    return find_project_root()
```

### 5.2 使用例

各project系コマンドの先頭で呼び出す:

```python
from mudsync.project import require_project, get_project_name

def command():
    project_root = require_project()
    proj_name = get_project_name(project_root)
    # ... 以降の処理
```

## 成果物

- `src/mudsync/project.py` - プロジェクト検出モジュール

## 検証

```bash
# gitリポジトリ内で
cd ~/projects/my-ml-project
uv run python -c "from mudsync.project import require_project; print(require_project())"
# /Users/k/projects/my-ml-project

# gitリポジトリ外で
cd /tmp
uv run python -c "from mudsync.project import require_project; print(require_project())"
# Error: Not a git repository...
```
