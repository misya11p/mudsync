# Task 7: Manage コマンド

## 概要

同期対象のファイル・ディレクトリを対話的に管理する `mudsync manage` コマンドを実装する。

## 実施内容

### 7.1 ファイル: `src/mudsync/sync_rules.py`

同期ルールの読み書きを担当するモジュール。

```python
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SyncRules:
    """同期ルール"""
    project_path: str
    excludes: list[str] = field(default_factory=list)


def get_state_dir() -> Path:
    """状態保存ディレクトリを返す ($XDG_STATE_HOME/mudsync/sync_rules)"""
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return state_home / "mudsync" / "sync_rules"


def project_hash(project_path: Path) -> str:
    """プロジェクトパスのハッシュを生成"""
    return hashlib.sha256(str(project_path.resolve()).encode()).hexdigest()[:16]


def load_rules(project_root: Path) -> SyncRules:
    """同期ルールを読み込む。存在しなければデフォルトを返す"""
    state_path = get_state_dir() / f"{project_hash(project_root)}.json"
    if not state_path.exists():
        return SyncRules(project_path=str(project_root.resolve()))
    data = json.loads(state_path.read_text())
    return SyncRules(**data)


def save_rules(rules: SyncRules) -> None:
    """同期ルールを保存"""
    state_path = get_state_dir() / f"{project_hash(Path(rules.project_path))}.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({
        "project_path": rules.project_path,
        "excludes": rules.excludes,
    }, indent=2))


def get_excludes(project_root: Path) -> list[str]:
    """除外リストを取得。rsyncの--excludeに渡す形式"""
    rules = load_rules(project_root)
    return rules.excludes
```

### 7.2 ファイル: `src/mudsync/commands/manage.py`

InquirerPyを使用した対話型ファイルブラウザ。

**実装方針:**

InquirerPyの`checkbox`や`select`はディレクトリナビゲーションには不向きなため、`prompt_toolkit`（InquirerPyの依存）を直接使用してカスタムUIを実装する。

```python
from pathlib import Path
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

from mudsync.project import require_project
from mudsync.sync_rules import SyncRules, load_rules, save_rules


# 状態管理
class FileBrowser:
    def __init__(self, project_root: Path, rules: SyncRules):
        self.project_root = project_root
        self.rules = rules
        self.current_dir = project_root
        self.cursor_index = 0
        self.items: list[Path] = []  # 現在のディレクトリのファイル一覧
        self.refresh_items()

    def refresh_items(self):
        """現在のディレクトリのファイル一覧を取得"""
        # .git は常に表示から除外（同期対象外固定）
        self.items = sorted([
            p for p in self.current_dir.iterdir()
            if p.name != ".git"
        ], key=lambda p: (not p.is_dir(), p.name.lower()))
        self.cursor_index = min(self.cursor_index, max(0, len(self.items) - 1))

    def is_excluded(self, path: Path) -> bool:
        """パスが除外リストにあるか判定"""
        rel = path.relative_to(self.project_root)
        rel_str = str(rel) + ("/" if path.is_dir() else "")
        return rel_str in self.rules.excludes

    def toggle_exclude(self, path: Path):
        """除外状態を切り替え"""
        rel = path.relative_to(self.project_root)
        rel_str = str(rel) + ("/" if path.is_dir() else "")
        if rel_str in self.rules.excludes:
            self.rules.excludes.remove(rel_str)
        else:
            self.rules.excludes.append(rel_str)

    def get_display_text(self):
        """表示用のテキストを生成"""
        lines = []
        # ヘッダー
        rel_current = self.current_dir.relative_to(self.project_root)
        lines.append(("class:header", f"📁 {rel_current or '.'}\n"))
        lines.append(("class:info", "↑↓/jk: move  ←→/hl: navigate  space: toggle  enter: save\n\n"))

        # ファイル一覧
        for i, item in enumerate(self.items):
            is_dir = item.is_dir()
            is_excluded = self.is_excluded(item)
            name = item.name + ("/" if is_dir else "")
            prefix = "▸ " if is_dir else "  "
            status = "[ ]" if is_excluded else "[✓]"

            if i == self.cursor_index:
                lines.append(("class:cursor", f"→ {status} {prefix}{name}\n"))
            else:
                lines.append(("", f"  {status} {prefix}{name}\n"))

        return lines

    def move_up(self):
        if self.cursor_index > 0:
            self.cursor_index -= 1

    def move_down(self):
        if self.cursor_index < len(self.items) - 1:
            self.cursor_index += 1

    def enter_dir(self):
        if self.items and self.items[self.cursor_index].is_dir():
            self.current_dir = self.items[self.cursor_index]
            self.cursor_index = 0
            self.refresh_items()

    def parent_dir(self):
        if self.current_dir != self.project_root:
            self.current_dir = self.current_dir.parent
            self.cursor_index = 0
            self.refresh_items()

    def toggle(self):
        if self.items:
            self.toggle_exclude(self.items[self.cursor_index])


def command():
    """同期対象ファイルを対話的に管理"""
    project_root = require_project()
    rules = load_rules(project_root)
    browser = FileBrowser(project_root, rules)

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("c-k")
    def _(event):
        browser.move_up()
        update_display()

    @kb.add("down")
    @kb.add("c-j")
    def _(event):
        browser.move_down()
        update_display()

    @kb.add("right")
    @kb.add("l")
    def _(event):
        browser.enter_dir()
        update_display()

    @kb.add("left")
    @kb.add("h")
    def _(event):
        browser.parent_dir()
        update_display()

    @kb.add(" ")
    def _(event):
        browser.toggle()
        update_display()

    @kb.add("enter")
    def _(event):
        save_rules(rules)
        event.app.exit(result="saved")

    @kb.add("c-c")
    def _(event):
        event.app.exit(result="cancelled")

    def update_display():
        buffer.text = "".join(t[1] for t in browser.get_display_text())

    style = Style.from_dict({
        "header": "bold #4fc3f7",
        "info": "#888888",
        "cursor": "bold #a5d6a7",
    })

    buffer = type("Buffer", (), {"text": ""})()
    # prompt_toolkitの正しいAPIで実装
    # 詳細は実装時に調整

    # 簡易実装: FormattedTextControlで
    def get_text():
        return browser.get_display_text()

    control = FormattedTextControl(get_text)
    layout = Layout(Window(content=control))
    app = Application(layout=layout, key_bindings=kb, style=style, full_screen=True)

    result = app.run()
    if result == "saved":
        from mudsync.utils import typer_echo
        typer_echo(f"Sync rules saved. ({len(rules.excludes)} excludes)")
```

**注意:** 上記は設計レベルの疑似コード。実際のprompt_toolkit実装では以下を正しく扱う必要がある:
- `Buffer` の正しい初期化方法
- `DynamicContainer` などの使用
- フルスクリーンアプリケーションの適切な設定

### 7.3 代替実装アプローチ

prompt_toolkitのフルスクリーンAPIが複雑な場合、InquirerPyの`inquirerpy.base.List`を拡張して実装する方法も検討する。ただしディレクトリナビゲーションが必要なので、カスタムUIが必須。

### 7.4 CLIへの登録

`src/mudsync/cli.py` に追記:

```python
from mudsync.commands import manage as manage_cmd

@app.command()
def manage():
    """Manage files to sync (interactive)"""
    manage_cmd.command()
```

## 成果物

- `src/mudsync/sync_rules.py` - 同期ルール管理モジュール
- `src/mudsync/commands/manage.py` - manageコマンド実装
- `src/mudsync/cli.py` - CLIエントリーポイント（更新）

## 検証

```bash
cd ~/projects/my-ml-project
uv run mudsync manage
# フルスクリーンUIが表示される
# j/kで移動、lでディレクトリに入る、hで上に戻る
# spaceで同期ON/OFF切り替え
# enterで保存

# 保存確認
cat ~/.local/state/mudsync/sync_rules/{hash}.json
# {"project_path": "/Users/k/projects/my-ml-project", "excludes": ["data/", "__pycache__/"]}
```
