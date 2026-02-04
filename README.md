# Python Syntax Highlighter

Minimal Python code editor with syntax highlighting and local autocomplete.
Built with **PySide6** for UI and **Pygments** for lexing.

## Quick Start
Install dependencies and run the app. The project ships with a minimal
`pygments` implementation so tests can run offline. For full highlighting and
the GUI, install the real packages when network access is available:

```bash
pip install PySide6 pygments  # optional
python main.py
```

## Autocomplete (Local)
Autocomplete runs locally with a transformers-compatible model in `model/`.
The folder must include weights plus tokenizer/config files (for example:
`config.json`, `generation_config.json`, `tokenizer.json`,
`tokenizer_config.json`, `merges.txt`, `vocab.json`, and a `.safetensors`
weights file named `model.safetensors`).

Install extra dependencies:

```bash
pip install torch transformers safetensors
```

Open **Settings → Autocomplete**:
- Enable autocomplete
- Set **Model folder** (default: `model/`)
- Choose **Device** (CPU/CUDA/Auto)
- Tune **Max new tokens**, **Context tokens**, **Debounce**, and
  **Allow suggestions in strings/comments**

CPU is supported but slower; reduce "Max new tokens" and increase "Debounce"
if suggestions feel laggy.

Autocomplete is hybrid:
- Fast symbol completions from the current file, Python keywords, and builtins
- LLM completion only when no symbol suggestion is available

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
