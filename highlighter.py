"""Syntax highlighter with theme support."""
from typing import List, Tuple, Dict
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token


class Lexer:
    """Simple lexer based on Pygments."""

    def __init__(self) -> None:
        self._lexer = PythonLexer()

    def get_tokens(self, text: str) -> List[Tuple[Token, str]]:
        """Return tokens for the given text."""
        return list(lex(text, self._lexer))


class Parser:
    """Trivial parser that returns tokens unchanged."""

    def parse(
        self, tokens: List[Tuple[Token, str]]
    ) -> List[Tuple[Token, str]]:
        return tokens


class Highlighter(QSyntaxHighlighter):
    """Qt syntax highlighter with theme support."""

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
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, _: str) -> None:
        self._rebuild_formats()
        self.rehighlight()

    def _rebuild_formats(self) -> None:
        """Build formats from current theme."""
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
        try:
            tokens = self._parser.parse(self._lexer.get_tokens(text))
        except Exception:
            return  # Skip highlighting on tokenization errors
        index = 0
        for token_type, token_value in tokens:
            length = len(token_value)
            fmt = self._resolve_format(token_type)
            if fmt:
                self.setFormat(index, length, fmt)
            index += length

    def _resolve_format(self, token_type):
        for ttype, fmt in self._formats.items():
            if token_type in ttype:
                return fmt
        return None
