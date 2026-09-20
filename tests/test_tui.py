"""Headless TUI tests via App.run_test()."""

from pathlib import Path

import pytest

from kanban_tui import board as board_mod
from kanban_tui.board import load_board, new_board, save_board
from kanban_tui.tui.app import BoardApp
from kanban_tui.tui.cards import ColumnPanel


@pytest.fixture()
async def tui(tmp_path: Path):
    path = tmp_path / "board.md"
    save_board(new_board(), path)
    app = BoardApp(path)
    async with app.run_test() as pilot:
        yield pilot, app


async def test_mounts_columns(tui):
    pilot, app = tui
    assert [p.column_name for p in app.column_panels()] == ["Backlog", "Doing", "Done"]


async def test_add_card_via_modal(tui):
    pilot, app = tui
    await pilot.press("a")
    from textual.widgets import Input

    for widget in app.screen.query(Input):
        widget.value = "write the thing #alpha"
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()
    b = load_board(app.board_path)
    assert b.columns[0].cards[0].title == "write the thing"
    assert b.columns[0].cards[0].tags == ("alpha",)


async def test_move_card_right(tui):
    pilot, app = tui
    app.apply(lambda b: board_mod.add_card(b, b.columns[0], "traveler"))
    await pilot.pause()
    panels = app.column_panels()
    panels[0].list_view.focus()
    panels[0].list_view.index = 0
    await pilot.pause()
    await pilot.press("l")
    await pilot.pause()
    b = load_board(app.board_path)
    assert b.columns[1].cards[0].title == "traveler"
    assert b.columns[0].cards == []


async def test_external_change_reloads(tui):
    pilot, app = tui
    external = new_board()
    board_mod.add_card(external, external.columns[2], "from the cli")
    save_board(external, app.board_path)
    await pilot.pause(1.5)  # mtime poll interval is 1.0s
    assert [p.column_name for p in app.column_panels()] == ["Backlog", "Doing", "Done"]
    done_lv = app.column_panels()[2].list_view
    assert done_lv.children
    assert done_lv.children[0].card.title == "from the cli"


async def test_command_palette_lists_board_commands(tui):
    pilot, app = tui
    board_mod.add_card(app.board, app.board.columns[0], "palette target #x")
    await pilot.pause()
    from kanban_tui.tui.commands import BoardCommands

    provider = BoardCommands(app)
    names = []
    async for hit in provider.discover():
        names.append(str(hit.display))
    assert any("add card in Backlog" in n for n in names)
    assert any("jump:" in n for n in names)