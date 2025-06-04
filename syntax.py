from typing import List, Tuple
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
    """Trivial parser that currently returns tokens unchanged."""

    def parse(
        self, tokens: List[Tuple[Token, str]]
    ) -> List[Tuple[Token, str]]:
        return tokens
