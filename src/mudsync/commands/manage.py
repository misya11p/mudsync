from pathlib import Path
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

from mudsync.project import require_project
from mudsync.sync_rules import SyncRules, load_rules, save_rules


class FileBrowser:
    def __init__(self, project_root: Path, rules: SyncRules):
        self.project_root = project_root
        self.rules = rules
        self.current_dir = project_root
        self.cursor_index = 0
        self.items: list[Path] = []
        self.refresh_items()

    def refresh_items(self):
        try:
            self.items = sorted(
                [p for p in self.current_dir.iterdir() if p.name != ".git"],
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except PermissionError:
            self.items = []
        self.cursor_index = min(self.cursor_index, max(0, len(self.items) - 1))

    def is_excluded(self, path: Path) -> bool:
        rel = path.relative_to(self.project_root)
        rel_str = str(rel) + ("/" if path.is_dir() else "")
        return rel_str in self.rules.excludes

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

            if i == self.cursor_index:
                lines.append(("class:cursor", f"> {status} {prefix}{name}\n"))
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
    project_root = require_project()
    rules = load_rules(project_root)
    browser = FileBrowser(project_root, rules)

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("c-k")
    def _(event):
        browser.move_up()

    @kb.add("down")
    @kb.add("c-j")
    def _(event):
        browser.move_down()

    @kb.add("right")
    @kb.add("l")
    def _(event):
        browser.enter_dir()

    @kb.add("left")
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
