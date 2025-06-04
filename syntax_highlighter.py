from typing import Dict
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from pygments.token import Token

from syntax import Lexer, Parser


class Highlighter(QSyntaxHighlighter):
    """Qt highlighter that uses Pygments tokens."""

    def __init__(self, document) -> None:
        super().__init__(document)
        self.lexer = Lexer()
        self.parser = Parser()
        self.formats: Dict[Token, QTextCharFormat] = {
            Token.Keyword: self._format("blue"),
            Token.Comment: self._format("green", italic=True),
            Token.Literal.String: self._format("orange"),
            Token.Operator: self._format("purple"),
            Token.Name.Function: self._format("brown", italic=True),
            Token.Name.Class: self._format("red", bold=True),
            Token.Name.Builtin: self._format("magenta"),
            Token.Name.Variable: self._format("darkcyan"),
        }

    def _format(
        self, color: str, bold: bool = False, italic: bool = False
    ) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def highlightBlock(self, text: str) -> None:  # type: ignore[override]
        tokens = self.parser.parse(self.lexer.get_tokens(text))
        index = 0
        for token_type, token_value in tokens:
            length = len(token_value)
            fmt = self._resolve_format(token_type)
            if fmt:
                self.setFormat(index, length, fmt)
            index += length

    def _resolve_format(self, token_type: Token):
        for ttype, fmt in self.formats.items():
            if token_type in ttype:
                return fmt
        return None
