"""Smoke tests for the kanban CLI (runs against a temp board via --board)."""

import json

import pytest

from kanban_tui.cli import main


@pytest.fixture()
def board_path(tmp_path):
    path = tmp_path / "board.md"
    main(["--board", str(path), "init"])
    return path


def test_init_then_add_and_list(board_path, capsys):
    main(["--board", str(board_path), "add", "Backlog", "first task", "--tags", "one,two"])
    out = capsys.readouterr().out
    assert "added [Backlog:1] first task #one #two" in out

    main(["--board", str(board_path), "list"])
    out = capsys.readouterr().out
    assert "[1] first task #one #two" in out


def test_move_and_json(board_path, capsys):
    main(["--board", str(board_path), "add", "Backlog", "task"])
    capsys.readouterr()
    main(["--board", str(board_path), "move", "Backlog", "1", "Doing", "--top"])
    capsys.readouterr()
    main(["--board", str(board_path), "list", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["columns"][1]["cards"][0]["title"] == "task"
    assert data["columns"][0]["cards"] == []


def test_missing_column_exit_1(board_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--board", str(board_path), "add", "Nope", "x"])
    assert exc.value.code == 1


def test_bad_index_exit_1(board_path, capsys):
    main(["--board", str(board_path), "add", "Backlog", "only"])
    with pytest.raises(SystemExit) as exc:
        main(["--board", str(board_path), "move", "Backlog", "5", "Doing"])
    assert exc.value.code == 1


def test_delete(board_path, capsys):
    main(["--board", str(board_path), "add", "Backlog", "doomed"])
    main(["--board", str(board_path), "delete", "Backlog", "1", "--yes"])
    out = capsys.readouterr().out
    assert "deleted [Backlog:1] doomed" in out