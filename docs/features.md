# Features

## Editor

- **Syntax highlighting** powered by Pygments (Python lexer)
- **Line numbers** with dynamic gutter width
- **Current line highlight**
- **Bracket matching** for `()`, `[]`, `{}`  with depth tracking
- **Auto-close brackets and quotes** — type `(` and `)` is inserted automatically; same for `[`, `{`, `"`, `'`
- **Auto-indent** — Enter copies the current indent level; adds an extra level after `:`
- **Duplicate line** — Ctrl+D duplicates the current line

## File Operations

- Open / Save / Save As with standard shortcuts
- **Drag & drop** a file onto the window to open it
- **CLI argument** — `python main.py file.py` opens the file on launch
- **Last file restore** — reopens the last file when launched without arguments
- **Trim trailing whitespace** on save (optional, in Settings)

## Find & Navigate

- **Find bar** with case-sensitive toggle
- **Go to line** dialog

## Appearance

- **Dark and light themes** (VS Code-inspired colors)
- **Auto theme** — follows the Windows system setting
- Theme switching via View menu or Settings

## Autocomplete (Optional)

- Hybrid: fast symbol completions (keywords, builtins, file symbols) + LLM ghost-text
- Runs fully offline with a local transformers-compatible model
- Works without `torch`/`transformers` installed — the editor starts normally
- See [Autocomplete](autocomplete.md) for setup

## Settings

Persistent settings stored in `~/.pyglow/settings.json`.
Configurable via **View > Settings** dialog:

- Font family and size
- Tab size and spaces vs tabs
- Show/hide line numbers
- Theme selection
- Trim whitespace on save
- All autocomplete parameters

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| Ctrl+O | Open file |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+X | Cut |
| Ctrl+C | Copy |
| Ctrl+V | Paste |
| Ctrl+A | Select all |
| Ctrl+F | Find |
| F3 | Find next |
| Shift+F3 | Find previous |
| Ctrl+G | Go to line |
| Ctrl+D | Duplicate line |
| Tab | Indent / accept autocomplete |
| Shift+Tab | Unindent |
| Esc | Dismiss autocomplete / close find bar |
