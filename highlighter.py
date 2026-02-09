"""Syntax highlighter with theme support.

Uses Pygments to tokenize Python code and maps tokens to Qt text
formats (colors, bold, italic) defined by the current color theme.

Architecture:
    Lexer   -> wraps Pygments PythonLexer, produces (Token, str) pairs
    Parser  -> pass-through (placeholder for future transforms)
    Highlighter -> QSyntaxHighlighter that applies formats per token
"""
from __future__ import annotations
from typing import List, Tuple, Dict
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token


class Lexer:
    """Thin wrapper around Pygments PythonLexer.

    Converts source text into a list of (token_type, value) tuples.
    """

    def __init__(self) -> None:
        self._lexer = PythonLexer()

    def get_tokens(self, text: str) -> List[Tuple[Token, str]]:
        """Tokenize *text* and return a list of (Token, str) pairs."""
        return list(lex(text, self._lexer))


class Parser:
    """Trivial parser that returns tokens unchanged.

    Exists as a hook for future AST-level transforms or filtering.
    """

    def parse(
        self, tokens: List[Tuple[Token, str]]
    ) -> List[Tuple[Token, str]]:
        """Return tokens as-is (no transformation)."""
        return tokens


class Highlighter(QSyntaxHighlighter):
    """Qt syntax highlighter that colors code using Pygments tokens.

    Listens to ThemeManager.theme_changed to rebuild formats and
    re-highlight the entire document when the user switches themes.
    """

    # Maps Pygments token types to (color_key, bold, italic).
    # color_key is looked up in the theme's color dictionary.
    TOKEN_MAP = {
        Token.Keyword: ('keyword', False, False),
        Token.Comment: ('comment', False, True),
        Token.Literal.String: ('string', False, False),
        Token.Operator: ('operator', False, False),
        Token.Name.Function: ('function', False, True),
        Token.Name.Class: ('class', True, False),
        Token.Name.Builtin: ('builtin', False, False),
        Token.Name.Variable: ('variable', False, False),
    }

    def __init__(self, document, theme_manager) -> None:
        super().__init__(document)
        self._theme = theme_manager
        self._lexer = Lexer()
        self._parser = Parser()
        self._formats: Dict[Token, QTextCharFormat] = {}
        self._rebuild_formats()
        # Re-highlight when theme changes
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, _: str) -> None:
        """Rebuild formats and re-highlight after a theme switch."""
        self._rebuild_formats()
        self.rehighlight()

    def _rebuild_formats(self) -> None:
        """Build QTextCharFormat objects from the current theme colors."""
        self._formats.clear()
        for token, (color_key, bold, italic) in self.TOKEN_MAP.items():
            fmt = QTextCharFormat()
            fmt.setForeground(self._theme.get_color(color_key))
            if bold:
                fmt.setFontWeight(QFont.Bold)
            if italic:
                fmt.setFontItalic(True)
            self._formats[token] = fmt

    def highlightBlock(self, text: str) -> None:
        """Highlight a single text block (line) by tokenizing it.

        On tokenization errors the block is left unstyled to avoid
        crashing the editor on incomplete or malformed code.
        """
        try:
            tokens = self._parser.parse(self._lexer.get_tokens(text))
        except Exception:
            return  # Skip highlighting on tokenization errors

        # Walk tokens and apply the matching format
        index = 0
        for token_type, token_value in tokens:
            length = len(token_value)
            fmt = self._resolve_format(token_type)
            if fmt:
                self.setFormat(index, length, fmt)
            index += length

    def _resolve_format(self, token_type):
        """Find the best matching format for *token_type*.

        Pygments tokens form a hierarchy (e.g. Token.Keyword.Namespace
        is a child of Token.Keyword), so we use the ``in`` operator to
        walk up the hierarchy until we find a registered format.
        """
        for ttype, fmt in self._formats.items():
            if token_type in ttype:
                return fmt
        return None
