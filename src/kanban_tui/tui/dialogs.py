"""Modal screens: add/edit/confirm, fuzzy jump, export view."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.fuzzy import Matcher
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListView, Static

from ..board import Board, Card
from .cards import CardItem


class _InputScreen(ModalScreen):
    """Base: a prompt + one Input, escape cancels, enter submits."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    CSS = """
    _InputScreen {
        align: center middle;
    }
    _InputScreen #dialog {
        width: 60%;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $surface;
    }
    .dialog-prompt {
        margin-bottom: 1;
    }
    .dialog-hint {
        color: $text-muted;
    }
    """

    def __init__(self, prompt: str, value: str = "", placeholder: str = "") -> None:
        super().__init__()
        self.prompt = prompt
        self.initial_value = value
        self.placeholder = placeholder

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.prompt, classes="dialog-prompt")
            yield Input(value=self.initial_value, placeholder=self.placeholder)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class AddCardScreen(_InputScreen):
    def __init__(self, column_name: str) -> None:
        super().__init__(f"Add card to {column_name}", placeholder="title #tag #tag")


class EditCardScreen(_InputScreen):
    def __init__(self, card: Card) -> None:
        super().__init__("Edit card", value=card.display)


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("y", "yes", "Yes", show=False),
        Binding("escape", "no", "No", show=False),
    ]

    CSS = """
    ConfirmScreen {
        align: center middle;
    }
    ConfirmScreen #dialog {
        width: 60%;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $surface;
    }
    .dialog-prompt {
        margin-bottom: 1;
    }
    .dialog-hint {
        color: $text-muted;
    }
    """

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.prompt, classes="dialog-prompt")
            yield Label("y = confirm · esc = cancel", classes="dialog-hint")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class JumpScreen(ModalScreen[Card | None]):
    """Fuzzy quick-jump: type to filter all cards, enter to go to it.

    Results are ranked with textual.fuzzy.Matcher on every keystroke —
    the same machinery the command palette uses.
    """

    CSS = """
    JumpScreen {
        align: center middle;
    }
    #jump-dialog {
        width: 80%;
        max-height: 70%;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $surface;
    }
    #jump-input {
        margin-bottom: 1;
    }
    #jump-results {
        height: auto;
        max-height: 12;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("up", "cursor_up", show=False),
        Binding("down", "cursor_down", show=False),
    ]

    def __init__(self, board: Board) -> None:
        super().__init__()
        self.board = board
        self._entries: list[tuple[float, Card, str]] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="jump-dialog"):
            yield Input(placeholder="jump to card…", id="jump-input")
            yield ListView(id="jump-results")

    def on_mount(self) -> None:
        self.populate("")

    def populate(self, query: str) -> None:
        matcher = Matcher(query) if query else None
        entries: list[tuple[float, Card, str]] = []
        for col, idx, card in self.board.find_cards():
            label = f"{col.name}[{idx}]  {card.display}"
            score = matcher.match(label) if matcher else 1.0
            if score > 0:
                entries.append((score, card, label))
        entries.sort(key=lambda e: -e[0])
        self._entries = entries
        lv = self.query_one("#jump-results", ListView)
        lv.clear()
        lv.extend(CardItem(card, idx) for _, card, _ in entries)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "jump-input":
            self.populate(event.value)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "jump-results":
            event.stop()
            self.dismiss(event.item.card)

    def action_cursor_up(self) -> None:
        self.query_one("#jump-results", ListView).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one("#jump-results", ListView).action_cursor_down()

    def action_cancel(self) -> None:
        self.dismiss(None)


class ExportScreen(ModalScreen[None]):
    """Deterministic plain-text board view — the agent-screenshot surface."""

    BINDINGS = [Binding("escape", "dismiss", "Close", show=False), Binding("e", "dismiss", show=False)]

    CSS = """
    ExportScreen {
        align: center middle;
        background: $surface;
    }
    #export-text {
        width: 1fr;
        height: 1fr;
        padding: 1 2;
        background: $surface;
    }
    """

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        yield Static(self.text, id="export-text")

    def action_dismiss(self) -> None:
        self.dismiss(None)