"""Column and card widgets.

Cards are Static-only ListItems so they render identically in the
terminal and over the web (textual-serve) — the "agent eyes" rule:
nothing that a screenshot can't capture reliably.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import ListItem, ListView, Static

from ..board import Card, Column


class CardItem(ListItem):
    def __init__(self, card: Card, index_1based: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.card = card
        self.index_1based = index_1based

    def compose(self) -> ComposeResult:
        yield Static(self.card.title, classes="card-title")
        if self.card.tags:
            yield Static(" ".join("#" + t for t in self.card.tags), classes="card-tags")


class ColumnPanel(Vertical):
    """Header + ListView for one kanban column."""

    def __init__(self, column: Column, **kwargs) -> None:
        kwargs.setdefault("classes", "kanban-column")
        super().__init__(**kwargs)
        self.column_name = column.name
        self.list_view = ListView(id=f"col-{column.name.lower()}")

    def compose(self) -> ComposeResult:
        yield Static(self.column_name.upper(), classes="column-header")
        yield self.list_view

    def populate(self, col: Column) -> None:
        self.list_view.clear()
        self.list_view.extend(CardItem(card, i) for i, card in enumerate(col.cards, 1))