"""Board file resolution: --board flag > KANBAN_BOARD env > ./board.md."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_BOARD_NAME = "board.md"


def get_board_path(flag: str | None = None) -> Path:
    if flag:
        return Path(flag).expanduser()
    env = os.environ.get("KANBAN_BOARD")
    if env:
        return Path(env).expanduser()
    return Path.cwd() / DEFAULT_BOARD_NAME