"""Pure Python editing logic — no Qt dependencies.

Extracted from CodeEditor so it can be tested in isolation and reused
by any View layer.
"""

# Maps open brackets to their close counterparts
BRACKETS = {'(': ')', '[': ']', '{': '}'}
# Reverse map: close bracket -> open bracket
BRACKETS_CLOSE = {v: k for k, v in BRACKETS.items()}


class EditorModel:
    """Stateless helper that encapsulates text-editing logic.

    All methods are static — there is no mutable state here.
    The View (CodeEditor) is responsible for reading/writing the
    actual document; these methods only transform plain strings.
    """

    @staticmethod
    def compute_newline_indent(line: str, tab_size: int, use_spaces: bool) -> str:
        """Return the text to insert after pressing Enter.

        Copies the current line's leading whitespace and adds one
        extra indent level when the line ends with ':'.

        Args:
            line:       The full text of the current line.
            tab_size:   Number of spaces per indent level.
            use_spaces: True → use spaces, False → use a real tab.

        Returns:
            A string starting with '\\n' followed by the new indentation.
        """
        indent = ''
        for c in line:
            if c in ' \t':
                indent += c
            else:
                break

        stripped = line.rstrip()
        if stripped.endswith(':'):
            if use_spaces:
                indent += ' ' * tab_size
            else:
                indent += '\t'

        return '\n' + indent

    @staticmethod
    def compute_tab_insert(tab_size: int, use_spaces: bool) -> str:
        """Return the string to insert when Tab is pressed.

        Args:
            tab_size:   Number of spaces per indent level.
            use_spaces: True → spaces, False → real tab character.
        """
        return ' ' * tab_size if use_spaces else '\t'

    @staticmethod
    def compute_backtab_removal(line: str, tab_size: int) -> int:
        """Return the number of characters to delete from the line start on Shift+Tab.

        Args:
            line:     The full text of the current line.
            tab_size: Number of spaces per indent level.

        Returns:
            Number of characters (spaces or 1 tab) to delete.
        """
        remove = 0
        for c in line:
            if c == ' ':
                remove += 1
                if remove >= tab_size:
                    break
            elif c == '\t':
                remove = 1
                break
            else:
                break
        return remove

    @staticmethod
    def find_matching_bracket(text: str, pos: int, char: str) -> int:
        """Find the position of the matching bracket using depth counting.

        Args:
            text: Full document text.
            pos:  Position of the bracket to match.
            char: The bracket character at *pos*.

        Returns:
            Index of the matching bracket, or -1 if not found.
        """
        if char in BRACKETS:
            target = BRACKETS[char]
            direction = 1
            start = pos + 1
            end = len(text)
        else:
            target = BRACKETS_CLOSE[char]
            direction = -1
            start = pos - 1
            end = -1

        depth = 1
        i = start
        while i != end:
            c = text[i]
            if c == char:
                depth += 1
            elif c == target:
                depth -= 1
                if depth == 0:
                    return i
            i += direction

        return -1

    @staticmethod
    def is_in_string_or_comment(text: str, cursor_pos: int) -> bool:
        """Return True if *cursor_pos* is inside a string literal or comment.

        Handles single-line strings and # comments only (not triple-quoted).

        Args:
            text:       Full document text.
            cursor_pos: Position of the cursor.
        """
        line_start = text.rfind('\n', 0, cursor_pos) + 1
        line = text[line_start:cursor_pos]
        in_single = False
        in_double = False
        escape = False
        i = 0
        while i < len(line):
            ch = line[i]
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif not in_double and ch == "'" and line[i:i + 3] != "'''":
                in_single = not in_single
            elif not in_single and ch == '"' and line[i:i + 3] != '"""':
                in_double = not in_double
            elif not in_single and not in_double and ch == '#':
                return True
            i += 1
        return in_single or in_double
