"""Web entrypoint — serve the TUI to browsers via textual-serve.

Each browser session spawns its own app process over a websocket;
the shared board.md keeps them in sync via the TUI's mtime polling.
"""

from __future__ import annotations

import argparse
import sys

from textual_serve.server import Server

from .paths import get_board_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="kanban-serve", description="Serve the kanban TUI on the web (textual-serve)"
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--board", help="path to board.md (default: $KANBAN_BOARD or ./board.md)")
    args = parser.parse_args(argv)

    board_path = get_board_path(args.board)
    command = f'"{sys.executable}" -m kanban_tui.tui.app --board "{board_path}"'
    Server(command, host=args.host, port=args.port, title="Kanban").serve()


if __name__ == "__main__":
    main()