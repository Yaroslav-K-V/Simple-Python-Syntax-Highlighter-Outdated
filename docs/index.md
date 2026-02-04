# Python Syntax Highlighter

The Python Syntax Highlighter Project is a GUI program designed to highlight the syntax of Python code. It uses **PySide6** for the interface and **Pygments** for lexing.

## Quick Start
Install dependencies and run the application.  The project ships with a
minimal `pygments` implementation so the tests can run offline.  If you want
the full highlighting and GUI, install the real packages when network access is
available:

```bash
pip install PySide6 pygments  # optional
python main.py
```

## Running Tests

Execute the unit tests with:

```bash
python -m unittest discover -s tests
```

## Docs

Build the minimal MkDocs site locally with:

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

The script stores the title/description as an annotated tag, pushes the tag to
`origin`, and can optionally push the current branch.
