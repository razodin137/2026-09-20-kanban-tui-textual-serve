"""Board model + Markdown round-trip. Pure stdlib — no textual imports.

Both the TUI and the CLI depend on this module; it is the contract
between "term for agents" and "web for people": one data file, board.md.

Format:
    # Board Title

    ## Backlog

    - write parser
    - fix favicon #bug #web

Columns are `## Name` sections in file order, cards are `- title` lines.
Every `#token` in a card's text is a tag; the rest is the title.
`- [ ]` checkbox syntax is accepted on read and normalized to `- ` on
write (a card's column IS its status). Unknown lines inside a section
are preserved verbatim and re-emitted after that section's cards.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

DEFAULT_COLUMNS = ("Backlog", "Doing", "Done")

_TAG_RE = re.compile(r"(?<!\S)#([A-Za-z0-9_-]+)")
_CARD_RE = re.compile(r"^- (?:\[[ xX]\] )?(.*)$")
_SECTION_RE = re.compile(r"^##\s+(.*?)\s*$")
_H1_RE = re.compile(r"^#\s+(.*?)\s*$")


@dataclass
class Card:
    title: str
    tags: tuple[str, ...] = ()

    @property
    def display(self) -> str:
        """Title with tags re-attached — the canonical one-line form."""
        if not self.tags:
            return self.title
        return f"{self.title} {' '.join('#' + t for t in self.tags)}"

    @classmethod
    def parse(cls, text: str) -> Card:
        title = text.strip()
        tags = tuple(t.lower() for t in _TAG_RE.findall(title))
        plain = _TAG_RE.sub("", title).strip()
        return cls(title=plain, tags=tags)


@dataclass
class Column:
    name: str
    cards: list[Card] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)


@dataclass
class Board:
    title: str = "Kanban"
    columns: list[Column] = field(default_factory=list)

    def column(self, name: str) -> Column | None:
        name_l = name.strip().lower()
        for col in self.columns:
            if col.name.lower() == name_l:
                return col
        return None

    def find_cards(self) -> list[tuple[Column, int, Card]]:
        """(column, 1-based index, card) for every card on the board."""
        return [
            (col, i, card)
            for col in self.columns
            for i, card in enumerate(col.cards, 1)
        ]


def parse_md(text: str) -> Board:
    board = Board(columns=[])
    current: Column | None = None
    for line in text.splitlines():
        if m := _H1_RE.match(line):
            if not board.title or board.title == "Kanban":
                board.title = m.group(1)
            continue
        if m := _SECTION_RE.match(line):
            name = m.group(1)
            existing = board.column(name)
            if existing is None:
                existing = Column(name=name)
                board.columns.append(existing)
            current = existing
            continue
        if current is None:
            continue  # preamble before the first section: dropped
        if m := _CARD_RE.match(line):
            current.cards.append(Card.parse(m.group(1)))
        elif line.strip():
            current.extras.append(line.rstrip())
        # blank lines collapse
    return board


def write_md(board: Board) -> str:
    out: list[str] = [f"# {board.title}", ""]
    for col in board.columns:
        out.append(f"## {col.name}")
        out.append("")
        for card in col.cards:
            out.append(f"- {card.display}")
        out.extend(col.extras)
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def load_board(path) -> Board:
    return parse_md(path.read_text(encoding="utf-8"))


def save_board(board: Board, path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(write_md(board), encoding="utf-8")
    os.replace(tmp, path)


def new_board(columns: tuple[str, ...] = DEFAULT_COLUMNS, title: str = "Kanban") -> Board:
    return Board(title=title, columns=[Column(name=c) for c in columns])


# --- operations ------------------------------------------------------------


def add_card(board: Board, col: Column, text: str) -> Card:
    card = Card.parse(text)
    col.cards.append(card)
    return card


def move_card(
    board: Board,
    src: Column,
    idx_1based: int,
    dst: Column,
    dst_idx_1based: int | None = None,
) -> None:
    """Move src.cards[idx-1] to dst; also reorders within a column."""
    pos = idx_1based - 1
    if not (0 <= pos < len(src.cards)):
        raise IndexError(f"{src.name} has no card {idx_1based}")
    if dst_idx_1based is None:
        dst_pos = len(dst.cards)
    else:
        dst_pos = dst_idx_1based - 1
        if not (0 <= dst_pos <= len(dst.cards)):
            raise IndexError(f"{dst.name} has no slot {dst_idx_1based}")
    card = src.cards.pop(pos)
    dst.cards.insert(dst_pos, card)


def delete_card(board: Board, col: Column, idx_1based: int) -> Card:
    pos = idx_1based - 1
    if not (0 <= pos < len(col.cards)):
        raise IndexError(f"{col.name} has no card {idx_1based}")
    return col.cards.pop(pos)