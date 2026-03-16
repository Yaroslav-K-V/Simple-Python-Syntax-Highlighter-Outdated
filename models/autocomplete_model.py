"""Pure Python text-analysis for autocomplete — no Qt dependencies.

Extracted from AutocompleteController so the logic can be tested
independently and reused without instantiating any Qt objects.
"""
from __future__ import annotations

import builtins
import keyword
import re


# Common dot-qualified identifiers surfaced as extra symbol candidates.
_COMMON_DOT_IDENTIFIERS = [
    "Console.WriteLine",
    "Console.Write",
    "System.out.println",
    "System.out.print",
    "System.out.printf",
    "String.format",
    "Math.Max",
    "Math.Min",
    "Math.Abs",
    "Math.Round",
    "Math.Floor",
    "Math.Ceiling",
]


class AutocompleteModel:
    """Stateful text-analysis model for symbol-based autocomplete.

    The only mutable state is a symbol cache that avoids re-scanning the
    document on every keystroke.  There are no Qt dependencies.
    """

    def __init__(self) -> None:
        self._last_symbol_text = ""
        self._symbol_cache: list[str] = []

    # ── Symbol extraction ────────────────────────────────────────

    def extract_symbols(self, text: str) -> list[str]:
        """Return all identifiers found in *text* plus keywords and builtins.

        Results are cached; the cache is invalidated when *text* changes.
        """
        if text == self._last_symbol_text:
            return self._symbol_cache
        tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text))
        tokens.update(keyword.kwlist)
        tokens.update(dir(builtins))
        tokens.update(_COMMON_DOT_IDENTIFIERS)
        self._last_symbol_text = text
        self._symbol_cache = list(tokens)
        return self._symbol_cache

    # ── Prefix helpers ───────────────────────────────────────────

    @staticmethod
    def word_prefix(text: str, cursor_pos: int) -> tuple[str, int]:
        """Return the identifier fragment immediately before *cursor_pos*.

        Returns:
            (prefix, start_index) where *prefix* == text[start_index:cursor_pos].
        """
        if cursor_pos <= 0:
            return "", cursor_pos
        start = cursor_pos
        while start > 0 and re.match(r"[A-Za-z0-9_]", text[start - 1]):
            start -= 1
        return text[start:cursor_pos], start

    @staticmethod
    def can_complete_here(text: str, cursor_pos: int) -> bool:
        """Return False if the cursor is directly followed by a word character.

        Completing in the middle of a word would produce garbled output.
        """
        if cursor_pos < len(text):
            if re.match(r"[A-Za-z0-9_]", text[cursor_pos]):
                return False
        return True

    @staticmethod
    def is_in_string_or_comment(text: str, cursor_pos: int) -> bool:
        """Return True if *cursor_pos* is inside a string literal or # comment.

        Handles single-line strings and # comments only (not triple-quoted).
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

    # ── Suggestion generation ────────────────────────────────────

    def symbol_suggestion(self, text: str, cursor_pos: int) -> str:
        """Return the completion suffix for the word prefix at *cursor_pos*.

        Returns an empty string when no appropriate suggestion is found.
        """
        if not self.can_complete_here(text, cursor_pos):
            return ""
        prefix, _ = self.word_prefix(text, cursor_pos)
        if not prefix:
            return self.assignment_symbol_suggestion(text, cursor_pos)
        symbols = self.extract_symbols(text)
        matches = [s for s in symbols if s.startswith(prefix) and s != prefix]
        if not matches:
            return ""
        matches.sort(key=lambda s: (-text.rfind(s), len(s), s))
        best = matches[0]
        return best[len(prefix):]

    @staticmethod
    def assignment_symbol_suggestion(text: str, cursor_pos: int) -> str:
        """Return a variable name suggestion after an assignment operator.

        Looks backwards for a pattern like ``var =`` in prior lines and
        suggests that variable name when the cursor follows an operator.
        """
        pos = cursor_pos - 1
        while pos >= 0 and text[pos].isspace():
            pos -= 1
        if pos < 0:
            return ""
        if text[pos] not in "=+-*/%&|^~,:()[]{}":
            return ""
        line_start = text.rfind('\n', 0, cursor_pos) + 1
        prior_text = text[:line_start]
        if not prior_text:
            return ""
        last_symbol = ""
        for match in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=", prior_text):
            eq_pos = match.end() - 1
            if eq_pos + 1 < len(prior_text) and prior_text[eq_pos + 1] == "=":
                continue
            last_symbol = match.group(1)
        return last_symbol

    def sanitize_suggestion(
        self,
        suggestion: str,
        prefix: str,
        max_chars: int = 80,
    ) -> str:
        """Clean and validate an LLM-generated *suggestion*.

        Strips leading newlines, removes duplicated prefix, enforces max
        length, and rejects obviously bad outputs (repetition, all-digits).

        Args:
            suggestion: Raw text from the model.
            prefix:     The text that immediately precedes the cursor.
            max_chars:  Maximum allowed suggestion length.

        Returns:
            Cleaned suggestion, or an empty string if it should be discarded.
        """
        suggestion = suggestion.lstrip('\r\n')
        if not suggestion:
            return ""
        word_pfx, _ = self.word_prefix(prefix, len(prefix))
        if word_pfx:
            suggestion = suggestion.lstrip()
            if not suggestion:
                return ""
            if suggestion.startswith(word_pfx):
                suggestion = suggestion[len(word_pfx):]
                if not suggestion:
                    return ""
            if not re.match(r"[A-Za-z0-9_]", suggestion[0]):
                return ""
        if len(suggestion) > max_chars:
            suggestion = suggestion[:max_chars]
        if len(suggestion) > 8:
            unique = set(suggestion)
            if len(unique) == 1:
                return ""
            if all(ch.isdigit() for ch in suggestion):
                return ""
        return suggestion
