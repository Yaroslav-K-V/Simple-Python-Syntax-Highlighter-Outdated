# Python Syntax Highlighter

The Python Syntax Highlighter Project is a GUI program designed to highlight the syntax of Python code. It uses **PyQt5** for the interface and **Pygments** for lexing.

## Quick Start
Install dependencies and run the application.  The project ships with a
minimal `pygments` implementation so the tests can run offline.  If you want
the full highlighting and GUI, install the real packages when network access is
available:

```bash
pip install PyQt5 pygments  # optional
python main.py
```

## Running Tests

Execute the unit tests with:

```bash
python -m unittest discover -s tests
```
