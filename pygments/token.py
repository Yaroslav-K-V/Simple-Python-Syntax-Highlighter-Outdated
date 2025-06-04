class _TokenType:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent

    def __contains__(self, item):
        while item is not None:
            if item is self:
                return True
            item = getattr(item, 'parent', None)
        return False

    def __repr__(self):
        return f'Token.{self.name}'


# Root token object
Token = _TokenType('Token')

# Basic token types
Token.Keyword = _TokenType('Keyword', Token)
Token.Comment = _TokenType('Comment', Token)
Token.Text = _TokenType('Text', Token)
Token.Operator = _TokenType('Operator', Token)

# Literals
Token.Literal = _TokenType('Literal', Token)
Token.Literal.String = _TokenType('String', Token.Literal)

# Names
Token.Name = _TokenType('Name', Token)
Token.Name.Function = _TokenType('Function', Token.Name)
Token.Name.Class = _TokenType('Class', Token.Name)
Token.Name.Builtin = _TokenType('Builtin', Token.Name)
Token.Name.Variable = _TokenType('Variable', Token.Name)
