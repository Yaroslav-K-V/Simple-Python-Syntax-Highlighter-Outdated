# PyGlow

Minimal Python code editor with syntax highlighting and local autocomplete.
Built with **PySide6** and **Pygments**.

## Features

- Syntax highlighting (Pygments), line numbers, current line highlight
- Bracket matching and auto-close for `()`, `[]`, `{}`, `""`, `''`
- Auto-indent, duplicate line (Ctrl+D)
- Find bar (Ctrl+F) with case sensitivity, go-to-line (Ctrl+G)
- Dark / light themes with Windows auto-detection
- Drag & drop file opening, CLI argument support, last file restore
- Optional local LLM autocomplete with ghost-text suggestions
- Persistent settings via `~/.pyglow/settings.json`

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Open a file directly:

```bash
python main.py script.py
```

## Autocomplete (Optional)

Autocomplete requires extra dependencies and a local model:

```bash
pip install torch transformers safetensors
```

Place a transformers-compatible model in `model/` and enable it in
**Settings > Autocomplete**. The editor works normally without these
dependencies — autocomplete is simply disabled.

See the [docs](docs/) for detailed setup and model selection guidance.

## Documentation

Build the MkDocs site locally:

```bash
pip install mkdocs mkdocs-material
mkdocs serve
```

## Release Tags

Generate and push a random release tag:

```powershell
.\scripts\new_random_tag.bat
```
