import unittest
from syntax import Lexer, Parser
from pygments.token import Token

class TestLexerParser(unittest.TestCase):
    def setUp(self):
        self.lexer = Lexer()
        self.parser = Parser()

    def test_lexer_returns_tokens(self):
        text = "def foo():\n    return 1"
        tokens = self.lexer.get_tokens(text)
        self.assertTrue(tokens)
        self.assertTrue(all(isinstance(t[1], str) for t in tokens))

    def test_parser_passthrough(self):
        sample = [(Token.Keyword, "def"), (Token.Text, " ")]
        parsed = self.parser.parse(sample)
        self.assertEqual(parsed, sample)

if __name__ == "__main__":
    unittest.main()
