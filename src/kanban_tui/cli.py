"""Companion CLI for agents — `kanban`. Shares board.md with the TUI.

Plain argparse, predictable stdout, exit codes: 0 ok, 1 bad column/index,
2 bad usage. Importable without textual.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import board as board_mod
from .paths import get_board_path

EXIT_OK, EXIT_NOT_FOUND, EXIT_USAGE = 0, 1, 2


def _load(path, create: bool = False):
    if not path.exists():
        if not create:
            print(f"error: board not found at {path} (run `kanban init`)", file=sys.stderr)
            raise SystemExit(EXIT_NOT_FOUND)
        b = board_mod.new_board()
        board_mod.save_board(b, path)
        return b
    return board_mod.load_board(path)


def _column_or_die(b: board_mod.Board, name: str) -> board_mod.Column:
    col = b.column(name)
    if col is None:
        names = ", ".join(c.name for c in b.columns)
        print(f"error: no column {name!r} (columns: {names})", file=sys.stderr)
        raise SystemExit(EXIT_NOT_FOUND)
    return col


# --- commands ---------------------------------------------------------------


def cmd_init(args) -> int:
    path = get_board_path(args.board)
    if path.exists() and not args.force:
        print(f"error: {path} already exists", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    cols = tuple(c.strip() for c in args.columns.split(",")) if args.columns else board_mod.DEFAULT_COLUMNS
    board_mod.save_board(board_mod.new_board(columns=cols), path)
    print(f"created {path} with columns: {', '.join(cols)}")
    return EXIT_OK


def cmd_add(args) -> int:
    b = _load(get_board_path(args.board))
    col = _column_or_die(b, args.column)
    text = " ".join(args.title)
    if args.tags:
        text = f"{text} {' '.join('#' + t.lstrip('#') for t in args.tags.split(','))}"
    card = board_mod.add_card(b, col, text)
    board_mod.save_board(b, get_board_path(args.board))
    print(f"added [{col.name}:{len(col.cards)}] {card.display}")
    return EXIT_OK


def cmd_move(args) -> int:
    b = _load(get_board_path(args.board))
    src = _column_or_die(b, args.column)
    if args.index < 1:
        print("error: --index must be >= 1", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    dst = _column_or_die(b, args.dest)
    dst_idx = None
    if args.index_dest:
        dst_idx = args.index_dest
    elif args.top:
        dst_idx = 1
    try:
        board_mod.move_card(b, src, args.index, dst, dst_idx)
    except IndexError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(EXIT_NOT_FOUND)
    board_mod.save_board(b, get_board_path(args.board))
    label = f"{args.dest}:{dst_idx}" if dst_idx else f"end of {args.dest}"
    print(f"moved [{src.name}:{args.index}] -> {label}")
    return EXIT_OK


def cmd_delete(args) -> int:
    b = _load(get_board_path(args.board))
    col = _column_or_die(b, args.column)
    if not args.yes:
        card = col.cards[args.index - 1] if 0 < args.index <= len(col.cards) else None
        if card is None:
            print(f"error: {col.name} has no card {args.index}", file=sys.stderr)
            raise SystemExit(EXIT_NOT_FOUND)
        answer = input(f"delete [{col.name}:{args.index}] {card.display}? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("aborted")
            return EXIT_OK
    try:
        card = board_mod.delete_card(b, col, args.index)
    except IndexError:
        print(f"error: {col.name} has no card {args.index}", file=sys.stderr)
        raise SystemExit(EXIT_NOT_FOUND)
    board_mod.save_board(b, get_board_path(args.board))
    print(f"deleted [{col.name}:{args.index}] {card.display}")
    return EXIT_OK


def cmd_list(args) -> int:
    b = _load(get_board_path(args.board))
    if args.json:
        print(json.dumps({
            "title": b.title,
            "columns": [
                {
                    "name": col.name,
                    "cards": [
                        {"title": c.title, "tags": list(c.tags), "index": i}
                        for i, c in enumerate(col.cards, 1)
                    ],
                }
                for col in b.columns
            ],
        }, indent=2))
        return EXIT_OK
    print(f"# {b.title}")
    for col in b.columns:
        print(f"\n{col.name}")
        if not col.cards:
            print("  (empty)")
        for i, c in enumerate(col.cards, 1):
            print(f"  [{i}] {c.display}")
    return EXIT_OK


def cmd_columns(args) -> int:
    b = _load(get_board_path(args.board))
    for i, col in enumerate(b.columns, 1):
        print(f"[{i}] {col.name} ({len(col.cards)})")
    return EXIT_OK


# --- parser -----------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kanban", description="kanban board CLI (shares board.md with the TUI)")
    p.add_argument("--board", help="path to board.md (default: $KANBAN_BOARD or ./board.md)")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("init", help="create a new board.md")
    sp.add_argument("--columns", help="comma-separated column names (default: Backlog,Doing,Done)")
    sp.add_argument("--force", action="store_true", help="overwrite existing board")
    sp.set_defaults(fn=cmd_init)

    sp = sub.add_parser("add", help="add a card (trailing #tags are parsed)")
    sp.add_argument("column")
    sp.add_argument("title", nargs="+")
    sp.add_argument("--tags", help="comma-separated tags (alternative to #tags in title)")
    sp.set_defaults(fn=cmd_add)

    sp = sub.add_parser("move", help="move a card between (or within) columns")
    sp.add_argument("column")
    sp.add_argument("index", type=int, help="1-based card index")
    sp.add_argument("dest")
    sp.add_argument("--index", dest="index_dest", type=int, help="1-based position in dest")
    sp.add_argument("--top", action="store_true", help="move to top of dest")
    sp.set_defaults(fn=cmd_move)

    sp = sub.add_parser("delete", help="delete a card")
    sp.add_argument("column")
    sp.add_argument("index", type=int)
    sp.add_argument("--yes", "-y", action="store_true", help="skip confirmation")
    sp.set_defaults(fn=cmd_delete)

    sp = sub.add_parser("list", help="print the board (human table, or --json)")
    sp.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    sp.set_defaults(fn=cmd_list)

    sp = sub.add_parser("columns", help="list column names")
    sp.set_defaults(fn=cmd_columns)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())