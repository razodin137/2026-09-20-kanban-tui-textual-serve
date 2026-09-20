"""Round-trip and operation tests for kanban_tui.board."""

from pathlib import Path

import pytest

from kanban_tui.board import (
    Board,
    Card,
    add_card,
    delete_card,
    load_board,
    move_card,
    new_board,
    parse_md,
    save_board,
    write_md,
)

SAMPLE = """\
# My Board

## Backlog

- write parser
- fix favicon #bug #web

## Doing

- [ ] kanban board
- [ ] export view #agent

## Done

- ship it #v1
"""


def test_parse_basic():
    b = parse_md(SAMPLE)
    assert b.title == "My Board"
    assert [c.name for c in b.columns] == ["Backlog", "Doing", "Done"]
    assert b.columns[0].cards[0].title == "write parser"
    assert b.columns[0].cards[1].tags == ("bug", "web")
    # checkbox syntax accepted on read, tag parsed
    assert b.columns[1].cards[1].tags == ("agent",)


def test_round_trip_is_fixed_point():
    """First write may normalize (`- [ ]` -> `- `); from then on, lossless."""
    once = write_md(parse_md(SAMPLE))
    assert write_md(parse_md(once)) == once


def test_round_trip_with_extras():
    text = "# T\n\n## A\n\n- one #x\nsome stray line\n\n## B\n\n- two\n"
    b = parse_md(text)
    assert b.columns[0].extras == ["some stray line"]
    assert write_md(b) == text


def test_duplicate_sections_merge():
    text = "# T\n\n## A\n\n- one\n\n## B\n\n- two\n\n## A\n\n- three\n"
    b = parse_md(text)
    assert len(b.columns) == 2
    assert [c.title for c in b.columns[0].cards] == ["one", "three"]


def test_unknown_sections_become_columns():
    text = "# T\n\n## Icebox\n\n- frozen\n"
    b = parse_md(text)
    assert [c.name for c in b.columns] == ["Icebox"]
    assert b.columns[0].cards[0].title == "frozen"


def test_tag_parse_rules():
    assert Card.parse("a #one b").tags == ("one",)
    assert Card.parse("#start").tags == ("start",)
    assert Card.parse("word#attached").tags == ()  # no space before # → not a tag
    assert Card.parse("no tags").tags == ()
    assert Card.parse("x #Bug #2fast").tags == ("bug", "2fast")


def test_card_display_round_trips():
    card = Card.parse("fix favicon #bug #web")
    assert card.display == "fix favicon #bug #web"


def test_checkbox_normalized_on_write():
    b = parse_md("# T\n\n## A\n\n- [x] done\n")
    assert write_md(b) == "# T\n\n## A\n\n- done\n"


def test_move_between_columns():
    b = parse_md(SAMPLE)
    backlog, doing = b.columns[0], b.columns[1]
    move_card(b, backlog, 1, doing, dst_idx_1based=1)
    assert doing.cards[0].title == "write parser"
    assert backlog.cards[0].title == "fix favicon"


def test_move_append_and_reorder():
    b = parse_md(SAMPLE)
    backlog = b.columns[0]
    move_card(b, backlog, 1, backlog)  # to bottom
    assert [c.title for c in backlog.cards] == ["fix favicon", "write parser"]
    move_card(b, backlog, 2, backlog, dst_idx_1based=1)  # back to top
    assert backlog.cards[0].title == "write parser"


def test_move_delete_bad_index_raises():
    b = parse_md(SAMPLE)
    with pytest.raises(IndexError):
        move_card(b, b.columns[0], 99, b.columns[1])
    with pytest.raises(IndexError):
        delete_card(b, b.columns[0], 5)


def test_find_cards_indexes():
    b = parse_md(SAMPLE)
    found = b.find_cards()
    assert found[0][:2] == (b.columns[0], 1)
    assert len(found) == 5


def test_save_load_round_trip(tmp_path: Path):
    path = tmp_path / "board.md"
    b = new_board()
    add_card(b, b.columns[0], "first #one")
    add_card(b, b.columns[1], "second")
    save_board(b, path)
    loaded = load_board(path)
    assert loaded.columns[0].cards[0].display == "first #one"
    assert [c.name for c in loaded.columns] == ["Backlog", "Doing", "Done"]
    assert path.with_name("board.md.tmp").exists() is False


def test_new_board_seed():
    b = new_board()
    assert [c.name for c in b.columns] == ["Backlog", "Doing", "Done"]
    assert all(not c.cards for c in b.columns)
    assert isinstance(b, Board)