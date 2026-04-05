import asyncio
import os
import threading
from pathlib import Path
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
import typer

from mudsync.project import require_project
from mudsync.sync_rules import SyncRules, load_rules, save_rules


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


def get_file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except (OSError, PermissionError):
        return 0


def count_dir_items(path: Path) -> int:
    try:
        count = 0
        for _ in path.iterdir():
            count += 1
            if count > 100:
                return count
        return count
    except (OSError, PermissionError):
        return 0


def calc_dir_size(path: Path) -> int:
    total = 0
    try:
        for p in path.rglob("*"):
            try:
                if not p.is_symlink():
                    total += p.stat().st_size
            except (OSError, PermissionError):
                pass
    except (OSError, PermissionError):
        pass
    return total


class FileBrowser:
    def __init__(self, project_root: Path, rules: SyncRules):
        self.project_root = project_root
        self.rules = rules
        self.current_dir = project_root
        self.cursor_index = 0
        self.items: list[Path] = []
        self.item_sizes: dict[Path, int] = {}
        self.dir_sizes: dict[Path, int] = {}
        self.size_loading: set[Path] = set()
        self.size_lock = threading.Lock()
        self.refresh_items()
        self._start_size_calculations()

    def refresh_items(self):
        try:
            self.items = sorted(
                [p for p in self.current_dir.iterdir() if p.name != ".git"],
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except PermissionError:
            self.items = []
        self.cursor_index = min(self.cursor_index, max(0, len(self.items) - 1))

        for item in self.items:
            if item not in self.item_sizes:
                if item.is_file():
                    self.item_sizes[item] = get_file_size(item)
                else:
                    self.item_sizes[item] = 0

    def _start_size_calculations(self):
        for item in self.items:
            if item.is_dir():
                item_count = count_dir_items(item)
                if item_count > 100 and not self.is_excluded(item):
                    rel_str = str(item.relative_to(self.project_root)) + "/"
                    if rel_str not in self.rules.excludes:
                        self.rules.excludes.append(rel_str)

                if item not in self.dir_sizes and item not in self.size_loading:
                    self._calc_dir_size_async(item)

    def _calc_dir_size_async(self, dir_path: Path):
        with self.size_lock:
            if dir_path in self.size_loading:
                return
            self.size_loading.add(dir_path)

        def worker():
            size = calc_dir_size(dir_path)
            with self.size_lock:
                self.dir_sizes[dir_path] = size
                self.item_sizes[dir_path] = size
                self.size_loading.discard(dir_path)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def is_excluded(self, path: Path) -> bool:
        rel = path.relative_to(self.project_root)
        rel_str = str(rel) + ("/" if path.is_dir() else "")
        if rel_str in self.rules.excludes:
            return True
        if path.is_dir():
            for exc in self.rules.excludes:
                if exc.endswith("/") and rel_str.startswith(exc):
                    return True
        return False

    def is_default_excluded(self, path: Path) -> bool:
        if path.is_file():
            size = self.item_sizes.get(path, get_file_size(path))
            return size > 10 * 1024 * 1024
        return False

    def toggle_exclude(self, path: Path):
        rel = path.relative_to(self.project_root)
        rel_str = str(rel) + ("/" if path.is_dir() else "")
        if rel_str in self.rules.excludes:
            self.rules.excludes.remove(rel_str)
        else:
            self.rules.excludes.append(rel_str)

    def get_display_text(self):
        lines = []
        rel_current = self.current_dir.relative_to(self.project_root)
        lines.append(("class:header", f"  {rel_current or '.'}\n"))
        lines.append(
            (
                "class:info",
                "up/down or j/k: move  right/l: enter dir  left/h: parent  space: toggle  enter: save  ctrl+c: cancel\n\n",
            )
        )

        for i, item in enumerate(self.items):
            is_dir = item.is_dir()
            is_excluded = self.is_excluded(item)
            name = item.name + ("/" if is_dir else "")
            prefix = "  " if is_dir else "  "
            status = "[ ]" if is_excluded else "[*]"

            size = self.item_sizes.get(item, 0)
            if is_dir and item in self.size_loading:
                size_str = "(calculating...)"
            else:
                size_str = format_size(size)

            if i == self.cursor_index:
                lines.append(
                    (
                        "class:cursor",
                        f"> {status} {prefix}{name:<30s} {size_str}\n",
                    )
                )
            else:
                lines.append(("", f"  {status} {prefix}{name:<30s} {size_str}\n"))

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
            self._start_size_calculations()

    def parent_dir(self):
        if self.current_dir != self.project_root:
            self.current_dir = self.current_dir.parent
            self.cursor_index = 0
            self.refresh_items()
            self._start_size_calculations()

    def toggle(self):
        if self.items:
            self.toggle_exclude(self.items[self.cursor_index])


def command():
    project_root = require_project()
    rules = load_rules(project_root)

    for item in project_root.iterdir():
        if item.name == ".git":
            continue
        if item.is_file():
            size = get_file_size(item)
            if size > 10 * 1024 * 1024:
                rel_str = str(item.relative_to(project_root))
                if rel_str not in rules.excludes:
                    rules.excludes.append(rel_str)
        elif item.is_dir():
            item_count = count_dir_items(item)
            if item_count > 100:
                rel_str = str(item.relative_to(project_root)) + "/"
                if rel_str not in rules.excludes:
                    rules.excludes.append(rel_str)

    browser = FileBrowser(project_root, rules)

    kb = KeyBindings()

    @kb.add("up")
    def _(event):
        browser.move_up()

    @kb.add("down")
    def _(event):
        browser.move_down()

    @kb.add("k")
    def _(event):
        browser.move_up()

    @kb.add("j")
    def _(event):
        browser.move_down()

    @kb.add("right")
    def _(event):
        browser.enter_dir()

    @kb.add("l")
    def _(event):
        browser.enter_dir()

    @kb.add("left")
    def _(event):
        browser.parent_dir()

    @kb.add("h")
    def _(event):
        browser.parent_dir()

    @kb.add(" ")
    def _(event):
        browser.toggle()

    @kb.add("enter")
    def _(event):
        save_rules(rules)
        event.app.exit(result="saved")

    @kb.add("c-c")
    def _(event):
        event.app.exit(result="cancelled")

    style = Style.from_dict(
        {
            "header": "bold #4fc3f7",
            "info": "#888888",
            "cursor": "bold #a5d6a7",
        }
    )

    control = FormattedTextControl(browser.get_display_text)
    layout = Layout(Window(content=control))
    app = Application(layout=layout, key_bindings=kb, style=style, full_screen=True)

    result = app.run()
    if result == "saved":
        typer.echo(f"Sync rules saved. ({len(rules.excludes)} excludes)")
