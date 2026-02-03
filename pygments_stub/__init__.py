"""Minimal stub of the Pygments package used for tests."""
from io import StringIO
from tokenize import generate_tokens, NAME, STRING, COMMENT, OP
import keyword

from .token import Token


class PythonLexer:
    """Placeholder lexer class for compatibility."""
    pass


def lex(text, lexer=None):
    """Very small subset of Pygments lex() functionality."""
    tokens = []
    stream = StringIO(text)
    prev_token = None
    for toknum, tokval, _, _, _ in generate_tokens(stream.readline):
        if toknum == NAME:
            if tokval in ("def", "class"):
                tokens.append((Token.Keyword, tokval))
                prev_token = tokval
                continue
            if prev_token == "def":
                tokens.append((Token.Name.Function, tokval))
            elif prev_token == "class":
                tokens.append((Token.Name.Class, tokval))
            elif tokval in keyword.kwlist:
                tokens.append((Token.Keyword, tokval))
            else:
                tokens.append((Token.Name, tokval))
            prev_token = None
        elif toknum == STRING:
            tokens.append((Token.Literal.String, tokval))
            prev_token = None
        elif toknum == COMMENT:
            tokens.append((Token.Comment, tokval))
            prev_token = None
        elif toknum == OP:
            tokens.append((Token.Operator, tokval))
            prev_token = None
        else:
            tokens.append((Token.Text, tokval))
            prev_token = None
    return tokens

__all__ = ["lex", "PythonLexer", "Token"]
