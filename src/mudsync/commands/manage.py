import threading
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
import typer

from mudsync.project import require_project
from mudsync.sync_rules import SyncRules, load_rules, save_rules

COMMON_EXCLUDES = [
    "__pycache__/",
    "node_modules/",
    ".venv/",
    ".ipynb_checkpoints/",
]


def format_size(size_bytes: int) -> tuple[str, str]:
    if size_bytes < 1024:
        return (f"{size_bytes:.1f}", "B")
    elif size_bytes < 1024 * 1024:
        return (f"{size_bytes / 1024:.1f}", "KB")
    elif size_bytes < 1024 * 1024 * 1024:
        return (f"{size_bytes / (1024 * 1024):.1f}", "MB")
    else:
        return (f"{size_bytes / (1024 * 1024 * 1024):.1f}", "GB")


SIZE_WIDTH = 8


def format_size_padded(size_bytes: int) -> str:
    num, unit = format_size(size_bytes)
    return f"{num:>5} {unit:>2}"


def get_file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except (OSError, PermissionError):
        return 0


def count_dir_items(path: Path) -> int:
    try:
        return sum(1 for _ in path.iterdir())
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


def _rel_str(path: Path, project_root: Path) -> str:
    rel = path.relative_to(project_root)
    return str(rel) + ("/" if path.is_dir() else "")


class FileBrowser:
    def __init__(self, project_root: Path, rules: SyncRules, app_ref: list):
        self.project_root = project_root
        self.rules = rules
        self.current_dir = project_root
        self.cursor_index = 0
        self.cursor_positions: dict[Path, int] = {}
        self.items: list[Path] = []
        self.item_sizes: dict[Path, int] = {}
        self.dir_sizes: dict[Path, int] = {}
        self.size_loading: set[Path] = set()
        self.size_lock = threading.Lock()
        self._app_ref = app_ref
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
        if self.current_dir in self.cursor_positions:
            self.cursor_index = min(
                self.cursor_positions[self.current_dir], max(0, len(self.items) - 1)
            )
        else:
            self.cursor_index = min(0, max(0, len(self.items) - 1))

        for item in self.items:
            if item not in self.item_sizes:
                if item.is_file():
                    self.item_sizes[item] = get_file_size(item)
                else:
                    self.item_sizes[item] = 0

    def _save_cursor_position(self):
        self.cursor_positions[self.current_dir] = self.cursor_index

    def _start_size_calculations(self):
        for item in self.items:
            if item.is_dir():
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
            app = self._app_ref[0]
            if app:
                app.invalidate()

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def is_excluded(self, path: Path) -> bool:
        rs = _rel_str(path, self.project_root)
        if rs in self.rules.excludes:
            return True
        if path.is_dir():
            for exc in self.rules.excludes:
                if exc.endswith("/") and rs.startswith(exc):
                    return True
        return False

    def all_children_excluded(self, dir_path: Path) -> bool:
        try:
            children = [p for p in dir_path.iterdir() if p.name != ".git"]
            if not children:
                return False
            return all(self.is_excluded(c) for c in children)
        except (OSError, PermissionError):
            return False

    def toggle_exclude(self, path: Path):
        if path.is_dir():
            if self.all_children_excluded(path):
                rs = _rel_str(path, self.project_root)
                if rs in self.rules.excludes:
                    self.rules.excludes.remove(rs)
                    for child in path.iterdir():
                        if child.name == ".git":
                            continue
                        crs = _rel_str(child, self.project_root)
                        if crs in self.rules.excludes:
                            self.rules.excludes.remove(crs)
                else:
                    self.rules.excludes.append(rs)
            else:
                for child in path.iterdir():
                    if child.name == ".git":
                        continue
                    crs = _rel_str(child, self.project_root)
                    if crs in self.rules.excludes:
                        self.rules.excludes.remove(crs)
                    else:
                        self.rules.excludes.append(crs)
        else:
            rs = _rel_str(path, self.project_root)
            if rs in self.rules.excludes:
                self.rules.excludes.remove(rs)
            else:
                self.rules.excludes.append(rs)

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

            size = self.item_sizes.get(item, 0)
            if is_dir and item in self.size_loading:
                size_str = "calc...".rjust(SIZE_WIDTH)
            else:
                size_str = format_size_padded(size)

            cursor_marker = "> " if i == self.cursor_index else "  "

            if is_excluded:
                lines.append(("", cursor_marker))
                lines.append(("class:excluded", f"{name:<30s} {size_str}\n"))
            else:
                lines.append(("", f"{cursor_marker}{name:<30s} {size_str}\n"))

        return lines

    def move_up(self):
        if self.cursor_index > 0:
            self.cursor_index -= 1

    def move_down(self):
        if self.cursor_index < len(self.items) - 1:
            self.cursor_index += 1

    def enter_dir(self):
        self._save_cursor_position()
        if self.items and self.items[self.cursor_index].is_dir():
            self.current_dir = self.items[self.cursor_index]
            self.cursor_index = 0
            self.refresh_items()
            self._start_size_calculations()

    def parent_dir(self):
        self._save_cursor_position()
        if self.current_dir != self.project_root:
            self.current_dir = self.current_dir.parent
            self.refresh_items()
            self._start_size_calculations()

    def toggle(self):
        if self.items:
            self.toggle_exclude(self.items[self.cursor_index])


def _compact_rules(rules: SyncRules, project_root: Path) -> SyncRules:
    excludes = set(rules.excludes)
    to_remove = set()
    for exc in excludes:
        if exc.endswith("/"):
            dir_path = project_root / exc.rstrip("/")
            if dir_path.is_dir():
                for child in dir_path.iterdir():
                    if child.name == ".git":
                        continue
                    crs = _rel_str(child, project_root)
                    if crs in excludes:
                        to_remove.add(crs)
    new_excludes = [e for e in rules.excludes if e not in to_remove]
    return SyncRules(project_path=rules.project_path, excludes=new_excludes)


def command():
    project_root = require_project()
    rules = load_rules(project_root)

    for item in project_root.iterdir():
        if item.name == ".git":
            continue
        if item.name in [e.rstrip("/") for e in COMMON_EXCLUDES]:
            rs = _rel_str(item, project_root)
            if rs not in rules.excludes:
                rules.excludes.append(rs)
        elif item.is_file():
            size = get_file_size(item)
            if size > 10 * 1024 * 1024:
                rs = _rel_str(item, project_root)
                if rs not in rules.excludes:
                    rules.excludes.append(rs)
        elif item.is_dir():
            item_count = count_dir_items(item)
            if item_count > 100:
                rs = _rel_str(item, project_root)
                if rs not in rules.excludes:
                    rules.excludes.append(rs)

    app_ref = [None]

    def get_display():
        return browser.get_display_text()

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
        event.app.invalidate()

    @kb.add("enter")
    def _(event):
        compacted = _compact_rules(rules, project_root)
        save_rules(compacted)
        event.app.exit(result="saved")

    @kb.add("c-c")
    def _(event):
        event.app.exit(result="cancelled")

    style = Style.from_dict(
        {
            "header": "bold #4fc3f7",
            "info": "#888888",
            "excluded": "ansibrightblack",
        }
    )

    browser = FileBrowser(project_root, rules, app_ref)

    control = FormattedTextControl(get_display)
    layout = Layout(Window(content=control))
    app = Application(layout=layout, key_bindings=kb, style=style, full_screen=True)
    app_ref[0] = app

    result = app.run()
    if result == "saved":
        typer.echo(f"Sync rules saved. ({len(rules.excludes)} excludes)")
