# Repository Guidelines

- Always run `python -m py_compile main.py syntax.py syntax_highlighter.py tests/test_syntax.py` to ensure all files compile.
- Run `pip install -r requirements.txt` if possible, though installation may fail in offline environments.
- Run the unit tests with `python -m unittest discover -s tests`.
- Follow PEP 8 coding style, keeping lines under 79 characters.
- Prefer f-strings, type annotations and async/await syntax where appropriate.
