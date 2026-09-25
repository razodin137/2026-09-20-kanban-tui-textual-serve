# kanban-tui — the terminal is for agents, the web is for people

A kanban board built with [Textual](https://textual.textualize.io/) — the terminal is for agents, the web is for people.

**Repository:** [razodin137/2026-09-20-kanban-tui-textual-serve](https://github.com/razodin137/2026-09-20-kanban-tui-textual-serve)

- **Terminal**: keyboard-driven TUI with fuzzy search everywhere (command palette `ctrl+p`, quick-jump `ctrl+k`), plus a companion CLI for agents to call from bash.
- **Web**: the same app served to browsers via [textual-serve](https://github.com/Textualize/textual-serve) — full keybindings and palette work over the websocket.
- **One data file**: everything reads and writes a single human-editable `board.md`.

## Quick start

```sh
uv sync

# terminal (for agents)
uv run kanban init          # create ./board.md
uv run kanban-tui           # run the TUI

# web (for people)
uv run kanban-serve --port 8000   # open http://localhost:8000
```

Use `--board path/to/board.md` (or the `KANBAN_BOARD` env var) to point every command at the same file. External edits — including from the CLI or your editor — are picked up by the TUI within ~1 second.

## The board file

```markdown
# My Board

## Backlog

- write parser
- fix favicon #bug #web

## Doing

- kanban board
```

- Columns are `## Name` sections, in file order. Any section name works.
- Cards are `- title` lines. Every `#token` is a tag; the rest is the title.
- A card's identity is `(column, 1-based index)` — not stored in the file.

## TUI keys

| key | action |
|---|---|
| `ctrl+p` | command palette — every board action, fuzzy-matched |
| `ctrl+k` | fuzzy jump to card |
| `a` | add card in focused column |
| `h` / `l` (or arrows) | move card to previous / next column |
| `shift+↑` / `shift+↓` | reorder card within column |
| `enter` | edit card title |
| `d` | delete card (confirm) |
| `e` | plain-text export view |
| `r` | reload board.md from disk |
| `q` | quit |

## CLI (for agents)

```sh
kanban init [--columns Backlog,Doing,Done]
kanban add <column> "title #tag" [--tags a,b]
kanban move <column> <index> <dest-column> [--index N | --top]
kanban delete <column> <index> [--yes]
kanban list [--json]      # --json: machine-readable board dump
kanban columns
```

## Development

```sh
uv run pytest        # board round-trips, CLI, headless TUI
```

Layout: `src/kanban_tui/board.py` (pure-stdlib model + markdown, shared by TUI and CLI), `cli.py` (argparse, no textual), `tui/` (app, widgets, palette provider, dialogs), `serve.py` (textual-serve entrypoint).