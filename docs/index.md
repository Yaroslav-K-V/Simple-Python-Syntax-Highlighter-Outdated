# Python Syntax Highlighter

Minimal Python code editor with syntax highlighting and local autocomplete.
Built with **PySide6** and **Pygments**.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Open a file directly from the command line:

```bash
python main.py script.py
```

Or drag and drop a file onto the editor window.

## What's Inside

- Syntax highlighting, line numbers, bracket matching, auto-close brackets
- Dark / light themes with Windows auto-detection
- Find bar, go-to-line, duplicate line, auto-indent
- Optional local LLM autocomplete (ghost-text suggestions)
- Persistent settings in `~/.python-highlighter/settings.json`

## Learn More

- [Features & Shortcuts](features.md) — full feature list and keyboard shortcuts
- [Autocomplete Setup](autocomplete.md) — how to set up local model autocomplete
- [Model Variants](models.md) — choosing the right model size
- [Guides & Troubleshooting](guides.md) — configuration, performance tuning, common errors
