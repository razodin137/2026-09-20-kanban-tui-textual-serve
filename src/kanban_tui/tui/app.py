"""BoardApp — the kanban TUI.

Terminal = for agents: every action is a fuzzy command-palette command,
keyboard moves are predictable, `e` toggles a plain-text export view,
and external edits to board.md are picked up within a second.
"""

from __future__ import annotations

import argparse

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header, ListView

from .. import board as board_mod
from ..paths import get_board_path
from .cards import CardItem, ColumnPanel
from .commands import BoardCommands
from .dialogs import AddCardScreen, ConfirmScreen, EditCardScreen, ExportScreen, JumpScreen


class BoardApp(App):
    TITLE = "Kanban"
    COMMANDS = App.COMMANDS | {BoardCommands}

    CSS = """
    #columns {
        height: 1fr;
    }
    .kanban-column {
        width: 1fr;
        height: 1fr;
        border: round $accent;
        padding: 0 1;
    }
    .kanban-column:focus-within {
        border: tall $accent;
        background: $surface;
    }
    .column-header {
        background: $accent;
        color: $background;
        text-align: center;
        padding: 0 1;
        margin-bottom: 1;
    }
    CardItem {
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
    }
    .card-title {
        width: 1fr;
    }
    .card-tags {
        color: $text-muted;
    }
    """

    BINDINGS = [
        ("a", "add_card", "Add card"),
        ("h", "move_left", "Move ←"),
        ("l", "move_right", "Move →"),
        ("shift+up", "reorder_up", "Reorder ↑"),
        ("shift+down", "reorder_down", "Reorder ↓"),
        ("d", "delete_card", "Delete"),
        ("r", "reload", "Reload"),
        ("e", "export_view", "Export"),
        ("ctrl+k", "jump", "Jump"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, board_path, **kwargs) -> None:
        super().__init__(**kwargs)
        self.board_path = board_path
        self.board = board_mod.new_board()
        self._last_mtime: int | None = None

    # --- lifecycle ----------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="columns"):
            for col in self.board.columns:
                yield ColumnPanel(col)
        yield Footer()

    def on_mount(self) -> None:
        self.reload_from_disk()
        self.set_interval(1.0, self.poll_mtime)

    # --- state funnel -------------------------------------------------------

    def apply(self, fn, *, source: str = "tui") -> None:
        """Mutate the board through one funnel: mutate -> save -> refresh."""
        fn(self.board)
        board_mod.save_board(self.board, self.board_path)
        self._last_mtime = self._mtime()
        self.refresh_views()

    def _mtime(self) -> int | None:
        try:
            return self.board_path.stat().st_mtime_ns
        except FileNotFoundError:
            return None

    def reload_from_disk(self) -> None:
        if self.board_path.exists():
            self.board = board_mod.load_board(self.board_path)
        else:
            board_mod.save_board(self.board, self.board_path)
        self._last_mtime = self._mtime()
        self.refresh_views()

    def poll_mtime(self) -> None:
        mtime = self._mtime()
        if mtime is not None and mtime != self._last_mtime:
            self.reload_from_disk()
            self.notify("Board reloaded from disk")

    # --- rendering ----------------------------------------------------------

    def column_panels(self) -> list[ColumnPanel]:
        return list(self.query(ColumnPanel).results())

    def refresh_views(self) -> None:
        # Remember cursor: (column name, card position) so a rebuild
        # doesn't jump focus to the top.
        focused = self.focused
        cursor = None
        if isinstance(focused, ColumnPanel):
            highlighted = focused.list_view.highlighted_child
            if highlighted is not None:
                cursor = (
                    focused.column_name,
                    focused.list_view.children.index(highlighted),
                )

        # Sync panels to columns. If names or order changed, rebuild the
        # row wholesale (columns rarely change; correctness beats cleverness).
        column_names = [c.name for c in self.board.columns]
        panels = self.column_panels()
        if [p.column_name for p in panels] != column_names:
            for panel in panels:
                panel.remove()
            columns_container = self.query_one("#columns", Horizontal)
            for col in self.board.columns:
                columns_container.mount(ColumnPanel(col))
            panels = self.column_panels()
        for panel, col in zip(panels, self.board.columns):
            panel.populate(col)

        # Restore cursor.
        if cursor:
            for panel in self.column_panels():
                if panel.column_name == cursor[0]:
                    children = panel.list_view.children
                    if cursor[1] < len(children):
                        panel.list_view.index = cursor[1]
                    if focused is panel:
                        panel.list_view.focus()
                    break

    # --- actions ------------------------------------------------------------

    @on(ListView.Selected)
    def open_card_editor(self, event: ListView.Selected) -> None:
        """Enter on a card opens the edit modal (ListView consumes the key)."""
        panel = event.list_view.parent
        if not isinstance(panel, ColumnPanel):
            return
        card = event.item.card
        col_name = panel.column_name
        idx = panel.list_view.children.index(event.item) + 1

        def edit(text: str | None) -> None:
            if text and text.strip():
                self.apply(
                    lambda b: b.column(col_name).cards.__setitem__(
                        idx - 1, board_mod.Card.parse(text)
                    )
                )
                self.notify("Card updated")

        self.push_screen(EditCardScreen(card), edit)

    def focused_panel(self) -> ColumnPanel | None:
        if isinstance(self.focused, ColumnPanel):
            return self.focused
        panels = self.column_panels()
        return panels[0] if panels else None

    def selected_item(self) -> tuple[ColumnPanel, int] | None:
        """(panel, 1-based card index) of the highlighted card, or None."""
        panel = self.focused_panel()
        if panel is None:
            return None
        lv = panel.list_view
        if lv.index is None:
            return None
        return panel, lv.index + 1

    def action_add_card(self, column: str | None = None) -> None:
        panel = (
            next((p for p in self.column_panels() if p.column_name == column), None)
            if column
            else self.focused_panel()
        )
        if panel is None:
            return
        col_name = panel.column_name

        def add(text: str | None) -> None:
            if text and text.strip():
                self.apply(lambda b: board_mod.add_card(b, b.column(col_name), text))
                self.notify(f"Added to {col_name}")

        self.push_screen(AddCardScreen(col_name), add)

    def action_edit_card(self) -> None:
        sel = self.selected_item()
        if sel is None:
            return
        panel, idx = sel
        card = panel.list_view.children[idx - 1].card

        def edit(text: str | None) -> None:
            if text and text.strip():
                new_card = board_mod.Card.parse(text)
                self.apply(
                    lambda b: b.column(panel.column_name).cards.__setitem__(idx - 1, new_card)
                )
                self.notify("Card updated")

        self.push_screen(EditCardScreen(card), edit)

    def action_move(self, delta: int) -> None:
        sel = self.selected_item()
        if sel is None:
            return
        panel, idx = sel
        panels = self.column_panels()
        pos = panels.index(panel)
        target = pos + delta
        if not 0 <= target < len(panels):
            self.notify(
                f"No column {'left' if delta < 0 else 'right'} of {panel.column_name}",
                severity="warning",
            )
            return
        dst_name = panels[target].column_name
        self.apply(
            lambda b: board_mod.move_card(b, b.column(panel.column_name), idx, b.column(dst_name))
        )
        self.notify(f"Moved to {dst_name}")

    def action_move_left(self) -> None:
        self.action_move(-1)

    def action_move_right(self) -> None:
        self.action_move(1)

    def action_reorder(self, delta: int) -> None:
        sel = self.selected_item()
        if sel is None:
            return
        panel, idx = sel
        new_idx = idx + delta
        if not 1 <= new_idx <= len(panel.list_view.children):
            return
        self.apply(
            lambda b: board_mod.move_card(
                b, b.column(panel.column_name), idx, b.column(panel.column_name), new_idx
            )
        )

    def action_reorder_up(self) -> None:
        self.action_reorder(-1)

    def action_reorder_down(self) -> None:
        self.action_reorder(1)

    def action_delete_card(self) -> None:
        sel = self.selected_item()
        if sel is None:
            return
        panel, idx = sel

        def do_delete(confirmed: bool | None) -> None:
            if confirmed:
                self.apply(lambda b: board_mod.delete_card(b, b.column(panel.column_name), idx))
                self.notify("Deleted")

        self.push_screen(ConfirmScreen(f"delete [{panel.column_name}:{idx}]?"), do_delete)

    def action_reload(self) -> None:
        self.reload_from_disk()
        self.notify("Board reloaded")

    def action_jump(self) -> None:
        self.push_screen(JumpScreen(self.board))

    def action_export_view(self) -> None:
        self.push_screen(ExportScreen(self.export_text()))

    def export_text(self) -> str:
        lines = [f"# {self.board.title}"]
        for col in self.board.columns:
            lines.append("")
            lines.append(col.name)
            if not col.cards:
                lines.append("  (empty)")
            for i, c in enumerate(col.cards, 1):
                lines.append(f"  [{i}] {c.display}")
        return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="kanban-tui", description="Kanban board TUI")
    parser.add_argument("--board", help="path to board.md (default: $KANBAN_BOARD or ./board.md)")
    args = parser.parse_args(argv)
    BoardApp(get_board_path(args.board)).run()


if __name__ == "__main__":
    main()