# Python Syntax Highlighter

Minimal Python code editor with syntax highlighting and local autocomplete.
Built with **PySide6** for UI and **Pygments** for lexing.

## Quick Start
Install dependencies and run the application. The project ships with a minimal
`pygments` implementation so tests can run offline. For full highlighting and
the GUI, install the real packages when network access is available:

```bash
pip install PySide6 pygments  # optional
python main.py
```

## Autocomplete (Local)
Autocomplete runs locally with a transformers-compatible model placed in
`model/`. The folder must include weights plus tokenizer/config files.

See:
- Autocomplete setup: `docs/autocomplete.md`
- Model variants: `docs/models.md`
- Guides & troubleshooting: `docs/guides.md`

## Running Tests
Execute unit tests with:

```bash
python -m unittest discover -s tests
```

## Docs
Build the MkDocs site locally with:

```bash
pip install mkdocs
mkdocs build
```

## Release Tags
Releases are created from Git tags starting with `v` (example: `vA7F3C9`).
Generate and push a random 6-character tag with:

```powershell
.\scripts\new_random_tag.bat
```
