"""Fuzzy command palette provider — every board action, one entry point.

The palette is the agents' interface: any board operation reachable
with ctrl+p and a few characters. Provider reads live app state at
search time, so the list always reflects the current board.
"""

from __future__ import annotations

from functools import partial
from typing import AsyncIterator, Callable, Iterable

from textual.command import DiscoveryHit, Hit, Hits, Provider

from ..board import Card, Column


def _card_label(col: Column, idx: int, card: Card) -> str:
    return f"{col.name}[{idx}]  {card.display}"


class BoardCommands(Provider):
    """Commands for board actions and per-card actions."""

    async def discover(self) -> AsyncIterator[DiscoveryHit]:
        app = self.app
        for name, callback, help_text in self._static_actions():
            yield DiscoveryHit(name, callback, help=help_text)
        for label, callback, help_text in self._card_actions():
            yield DiscoveryHit(label, callback, help=help_text)

    async def search(self, query: str) -> AsyncIterator[Hit]:
        matcher = self.matcher(query)

        def filtered(pairs: Iterable[tuple[str, Callable, str | None]]):
            out = []
            for label, callback, help_text in pairs:
                score = matcher.match(label)
                if score > 0:
                    out.append((score, label, callback, help_text))
            out.sort(key=lambda e: -e[0])
            return out

        for score, label, callback, help_text in (
            filtered(self._static_actions()) + filtered(self._card_actions())
        ):
            yield Hit(score, matcher.highlight(label), callback, help=help_text)

    # --- candidate builders -------------------------------------------------

    def _static_actions(self) -> list[tuple[str, Callable, str | None]]:
        app = self.app
        actions: list[tuple[str, Callable, str | None]] = []
        for col in app.board.columns:
            actions.append(
                (
                    f"add card in {col.name}",
                    partial(app.action_add_card, col.name),
                    f"open add dialog for {col.name}",
                )
            )
        actions.extend(
            [
                ("jump to card", app.action_jump, "fuzzy jump (ctrl+k)"),
                ("reload board", app.action_reload, "re-read board.md from disk"),
                ("export board", app.action_export_view, "plain-text board view"),
                ("quit", app.action_quit, "close the app"),
            ]
        )
        return actions

    def _card_actions(self) -> list[tuple[str, Callable, str | None]]:
        app = self.app
        actions: list[tuple[str, Callable, str | None]] = []
        for col, idx, card in app.board.find_cards():
            label = _card_label(col, idx, card)
            # Jump to the card: focus its column list and highlight it.
            def jump(panel_name=col.name, item_idx=idx, _app=app):
                for panel in _app.column_panels():
                    if panel.column_name == panel_name:
                        lv = panel.list_view
                        if 0 <= item_idx - 1 < len(lv.children):
                            lv.index = item_idx - 1
                        lv.focus()
                        break

            actions.append((f"jump: {label}", jump, f"go to this card in {col.name}"))
            # Add a card right after this one in the same column.
            actions.append(
                (
                    f"add after: {label}",
                    partial(app.action_add_card, col.name),
                    "add a card to this column",
                )
            )
        return actions