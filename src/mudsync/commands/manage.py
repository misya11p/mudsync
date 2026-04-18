import fnmatch
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
from mudsync.sync_rules import (
    ProjectConfig,
    DEFAULT_GLOBAL_EXCLUDES,
    load_project_config,
    require_project_config,
    save_project_config,
)


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
    def __init__(
        self,
        project_root: Path,
        project_config: ProjectConfig,
        app_ref: list,
    ):
        self.project_root = project_root
        self.project_config = project_config
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

    def _is_global_excluded(self, path: Path) -> bool:
        name = path.name
        for pattern in DEFAULT_GLOBAL_EXCLUDES:
            base = pattern.rstrip("/")
            if name == base:
                return True
            if "*" in pattern or "?" in pattern:
                if fnmatch.fnmatch(name, pattern):
                    return True
        return False

    def refresh_items(self):
        try:
            self.items = sorted(
                [
                    p
                    for p in self.current_dir.iterdir()
                    if not self._is_global_excluded(p)
                ],
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

    def is_data_included(self, path: Path) -> bool:
        if self._is_global_excluded(path):
            return False
        rs = _rel_str(path, self.project_root)
        if rs in self.project_config.data_includes:
            return True
        for di in self.project_config.data_includes:
            if di.endswith("/") and rs.startswith(di):
                return True
        return False

    def _find_parent_data_inclusion(self, path: Path) -> str | None:
        if self._is_global_excluded(path):
            return None
        rs = _rel_str(path, self.project_root)
        for di in self.project_config.data_includes:
            if di.endswith("/") and rs.startswith(di):
                return di
        return None

    def is_excluded(self, path: Path) -> bool:
        if self.is_data_included(path):
            return False
        if self._is_global_excluded(path):
            return True
        rs = _rel_str(path, self.project_root)
        if rs in self.project_config.excludes:
            return True
        for exc in self.project_config.excludes:
            if exc.endswith("/") and rs.startswith(exc):
                return True
        return False

    def _find_parent_exclusion(self, path: Path) -> str | None:
        if self._is_global_excluded(path):
            return "__global__"
        rs = _rel_str(path, self.project_root)
        for exc in self.project_config.excludes:
            if exc.endswith("/") and rs.startswith(exc):
                return exc
        return None

    def get_item_state(self, path: Path) -> str:
        if self.is_data_included(path):
            return "data"
        if self.is_excluded(path):
            return "exclude"
        return "include"

    def get_dir_state(self, path: Path) -> str:
        if self.is_data_included(path):
            return "data"
        if self.is_excluded(path):
            return "exclude"
        try:
            children = [p for p in path.iterdir() if not self._is_global_excluded(p)]
        except (OSError, PermissionError):
            return "include"
        if not children:
            return "include"
        child_states = set()
        for c in children:
            if c.is_dir():
                child_states.add(self.get_dir_state(c))
            else:
                child_states.add(self.get_item_state(c))
        if child_states == {"exclude"}:
            return "exclude"
        if child_states == {"data"}:
            return "data"
        all_included_or_data = all(s in ("include", "data") for s in child_states)
        if all_included_or_data and "data" not in child_states:
            return "include"
        if all_included_or_data and "data" in child_states:
            return "half_data"
        return "half_include"

    def toggle_exclude(self, path: Path):
        if self._is_global_excluded(path):
            return
        if self.is_data_included(path):
            self._remove_data_inclusion(path)
        if path.is_dir():
            rs = _rel_str(path, self.project_root)
            state = self.get_dir_state(path)
            parent_exc = self._find_parent_exclusion(path)
            if state == "exclude":
                if rs in self.project_config.excludes:
                    self.project_config.excludes.remove(rs)
                    for child in path.rglob("*"):
                        if self._is_global_excluded(child):
                            continue
                        crs = _rel_str(child, self.project_root)
                        if crs in self.project_config.excludes:
                            self.project_config.excludes.remove(crs)
                elif parent_exc and parent_exc != "__global__":
                    self.project_config.excludes.remove(parent_exc)
                    parent_dir = self.project_root / parent_exc.rstrip("/")
                    for sibling in parent_dir.iterdir():
                        if self._is_global_excluded(sibling) or sibling == path:
                            continue
                        crs = _rel_str(sibling, self.project_root)
                        if crs not in self.project_config.excludes:
                            self.project_config.excludes.append(crs)
            elif state == "half_include":
                for child in path.rglob("*"):
                    if self._is_global_excluded(child):
                        continue
                    crs = _rel_str(child, self.project_root)
                    if crs in self.project_config.excludes:
                        self.project_config.excludes.remove(crs)
            else:
                self.project_config.excludes.append(rs)
        else:
            rs = _rel_str(path, self.project_root)
            if rs in self.project_config.excludes:
                self.project_config.excludes.remove(rs)
            elif parent_exc := self._find_parent_exclusion(path):
                if parent_exc == "__global__":
                    return
                self.project_config.excludes.remove(parent_exc)
                parent_dir = self.project_root / parent_exc.rstrip("/")
                for sibling in parent_dir.iterdir():
                    if self._is_global_excluded(sibling) or sibling == path:
                        continue
                    crs = _rel_str(sibling, self.project_root)
                    if crs not in self.project_config.excludes:
                        self.project_config.excludes.append(crs)
            else:
                self.project_config.excludes.append(rs)

    def _remove_data_inclusion(self, path: Path):
        rs = _rel_str(path, self.project_root)
        if rs in self.project_config.data_includes:
            self.project_config.data_includes.remove(rs)
        else:
            parent_di = self._find_parent_data_inclusion(path)
            if parent_di:
                self.project_config.data_includes.remove(parent_di)
                parent_dir = self.project_root / parent_di.rstrip("/")
                for sibling in parent_dir.iterdir():
                    if self._is_global_excluded(sibling) or sibling == path:
                        continue
                    srs = _rel_str(sibling, self.project_root)
                    if srs not in self.project_config.data_includes:
                        self.project_config.data_includes.append(srs)
        if path.is_dir():
            for child in path.rglob("*"):
                if self._is_global_excluded(child):
                    continue
                crs = _rel_str(child, self.project_root)
                if crs in self.project_config.data_includes:
                    self.project_config.data_includes.remove(crs)

    def toggle_data(self, path: Path):
        if self._is_global_excluded(path):
            return
        rs = _rel_str(path, self.project_root)
        if self.is_data_included(path):
            self._remove_data_inclusion(path)
        else:
            if self.is_excluded(path):
                if rs in self.project_config.excludes:
                    self.project_config.excludes.remove(rs)
                else:
                    parent_exc = self._find_parent_exclusion(path)
                    if parent_exc and parent_exc != "__global__":
                        self.project_config.excludes.remove(parent_exc)
                        parent_dir = self.project_root / parent_exc.rstrip("/")
                        for sibling in parent_dir.iterdir():
                            if self._is_global_excluded(sibling) or sibling == path:
                                continue
                            srs = _rel_str(sibling, self.project_root)
                            if srs not in self.project_config.excludes:
                                self.project_config.excludes.append(srs)
                if path.is_dir():
                    for child in path.rglob("*"):
                        if self._is_global_excluded(child):
                            continue
                        crs = _rel_str(child, self.project_root)
                        if crs in self.project_config.excludes:
                            self.project_config.excludes.remove(crs)
            self.project_config.data_includes.append(rs)
            if path.is_dir():
                for child in path.rglob("*"):
                    if self._is_global_excluded(child):
                        continue
                    crs = _rel_str(child, self.project_root)
                    if crs in self.project_config.data_includes:
                        self.project_config.data_includes.remove(crs)

    def get_display_text(self):
        lines = []
        rel_current = self.current_dir.relative_to(self.project_root)
        lines.append(("class:header", f"  {rel_current or '.'}\n"))
        lines.append(
            (
                "class:info",
                "up/down or j/k: move  right/l: enter dir  left/h: parent  space: toggle sync  d: toggle data  enter: save  esc/q/ctrl+c: cancel\n\n",
            )
        )

        for i, item in enumerate(self.items):
            is_dir = item.is_dir()
            name = item.name + ("/" if is_dir else "")

            if is_dir:
                state = self.get_dir_state(item)
                if state == "exclude":
                    display_name = name
                    style_class = "class:excluded"
                elif state == "data":
                    display_name = name + "*"
                    style_class = "class:data"
                elif state == "include":
                    display_name = name + "*"
                    style_class = "class:included"
                elif state == "half_data":
                    display_name = name
                    style_class = "class:data"
                else:
                    display_name = name
                    style_class = "class:included"
            else:
                state = self.get_item_state(item)
                if state == "exclude":
                    display_name = name
                    style_class = "class:excluded"
                elif state == "data":
                    display_name = name
                    style_class = "class:data"
                else:
                    display_name = name
                    style_class = "class:included"

            size = self.item_sizes.get(item, 0)
            if is_dir and item in self.size_loading:
                size_str = "calc...".rjust(SIZE_WIDTH)
            else:
                size_str = format_size_padded(size)

            cursor_marker = "> " if i == self.cursor_index else "  "

            lines.append(
                (style_class, f"{cursor_marker}{display_name:<30s} {size_str}\n")
            )

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

    def toggle_data_item(self):
        if self.items:
            self.toggle_data(self.items[self.cursor_index])


def _compact_rules(config: ProjectConfig, project_root: Path) -> ProjectConfig:
    excludes = set(config.excludes)
    to_remove = set()
    for exc in excludes:
        if exc.endswith("/"):
            dir_path = project_root / exc.rstrip("/")
            if dir_path.is_dir():
                for child in dir_path.iterdir():
                    if any(
                        child.name == p.rstrip("/")
                        or ("*" in p and fnmatch.fnmatch(child.name, p))
                        for p in DEFAULT_GLOBAL_EXCLUDES
                    ):
                        continue
                    crs = _rel_str(child, project_root)
                    if crs in excludes:
                        to_remove.add(crs)
    new_excludes = [e for e in config.excludes if e not in to_remove]

    data_includes = set(config.data_includes)
    to_remove_data = set()
    for di in data_includes:
        if di.endswith("/"):
            dir_path = project_root / di.rstrip("/")
            if dir_path.is_dir():
                for child in dir_path.iterdir():
                    if any(
                        child.name == p.rstrip("/")
                        or ("*" in p and fnmatch.fnmatch(child.name, p))
                        for p in DEFAULT_GLOBAL_EXCLUDES
                    ):
                        continue
                    crs = _rel_str(child, project_root)
                    if crs in data_includes:
                        to_remove_data.add(crs)
    new_data_includes = [d for d in config.data_includes if d not in to_remove_data]

    return ProjectConfig(
        server=config.server,
        remote_path=config.remote_path,
        excludes=new_excludes,
        data_dir=config.data_dir,
        data_includes=new_data_includes,
    )


def command():
    project_root = require_project()
    project_config = require_project_config(project_root)

    for item in project_root.iterdir():
        if item.is_file():
            size = get_file_size(item)
            if size > 10 * 1024 * 1024:
                rs = _rel_str(item, project_root)
                if rs not in project_config.excludes:
                    project_config.excludes.append(rs)
        elif item.is_dir():
            item_count = count_dir_items(item)
            if item_count > 100:
                rs = _rel_str(item, project_root)
                if rs not in project_config.excludes:
                    project_config.excludes.append(rs)

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

    @kb.add("space")
    def _(event):
        browser.toggle()
        event.app.invalidate()

    @kb.add("d")
    def _(event):
        browser.toggle_data_item()
        event.app.invalidate()

    @kb.add("enter")
    def _(event):
        compacted = _compact_rules(project_config, project_root)
        save_project_config(project_root, compacted)
        event.app.exit(result="saved")

    @kb.add("c-c")
    def _(event):
        event.app.exit(result="cancelled")

    @kb.add("escape")
    def _(event):
        event.app.exit(result="cancelled")

    @kb.add("q")
    def _(event):
        event.app.exit(result="cancelled")

    style = Style.from_dict(
        {
            "header": "bold #4fc3f7",
            "info": "#888888",
            "excluded": "#888888",
            "included": "#4caf50",
            "data": "#ff9800",
        }
    )

    browser = FileBrowser(project_root, project_config, app_ref)

    control = FormattedTextControl(get_display)
    layout = Layout(Window(content=control))
    app = Application(layout=layout, key_bindings=kb, style=style, full_screen=True)
    app_ref[0] = app

    result = app.run()
    if result == "saved":
        typer.echo(
            f"Sync rules saved. ({len(project_config.excludes)} excludes, {len(project_config.data_includes)} data)"
        )
    elif result == "cancelled":
        typer.echo("Sync rules update cancelled.")
