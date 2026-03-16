"""Find & Replace controller — all search logic isolated from FindBar UI."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import (
    QTextCursor, QTextCharFormat, QColor, QTextDocument,
)
from PySide6.QtWidgets import QTextEdit

from services.search_service import SearchService


class FindController(QObject):
    """Owns find/replace/highlight logic for the editor.

    FindBar (View) emits user actions; FindController handles them and
    updates the editor + the match-count label in FindBar.

    Signals:
        match_count_updated(str): Display string like '3/7' or '0/0'.
    """

    match_count_updated = Signal(str)

    def __init__(self, editor, theme_manager) -> None:
        super().__init__()
        self._editor = editor
        self._theme = theme_manager
        self._match_positions: list[int] = []
        self._last_query = ""
        self._last_case = False

    # ── Public API ────────────────────────────────────────────────

    def highlight_all(self, query: str, case_sensitive: bool) -> None:
        """Highlight every match; update count label and match list."""
        self._last_query = query
        self._last_case = case_sensitive
        self._do_highlight(query, case_sensitive)

    def clear_highlights(self) -> None:
        """Remove all find highlights from the editor."""
        self._match_positions = []
        self._editor.set_find_selections([])
        self.match_count_updated.emit('')

    def find_next(self, query: str, case_sensitive: bool) -> None:
        """Move the cursor to the next match (wraps to top)."""
        if not query:
            return
        flags = self._build_flags(case_sensitive)
        if not self._editor.find(query, flags):
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self._editor.setTextCursor(cursor)
            self._editor.find(query, flags)
        self._emit_match_label(query)

    def find_prev(self, query: str, case_sensitive: bool) -> None:
        """Move the cursor to the previous match (wraps to end)."""
        if not query:
            return
        flags = self._build_flags(case_sensitive) | QTextDocument.FindBackward
        if not self._editor.find(query, flags):
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self._editor.setTextCursor(cursor)
            self._editor.find(query, flags)
        self._emit_match_label(query)

    def replace_current(
        self, search: str, replace: str, case_sensitive: bool
    ) -> None:
        """Replace the current selection if it matches *search*, then advance."""
        if not search:
            return
        cursor = self._editor.textCursor()
        if not cursor.hasSelection():
            self.find_next(search, case_sensitive)
            return
        selected = cursor.selectedText()
        match = (selected == search) if case_sensitive else (selected.lower() == search.lower())
        if match:
            cursor.insertText(replace)
            self._do_highlight(search, case_sensitive)
        self.find_next(search, case_sensitive)

    def replace_all(self, search: str, replace: str, case_sensitive: bool) -> int:
        """Replace every match as a single undo operation.

        Returns the number of replacements made.
        """
        if not search:
            return 0
        flags = self._build_flags(case_sensitive)
        doc = self._editor.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        count = 0
        cursor.beginEditBlock()
        while True:
            cursor = doc.find(search, cursor, flags)
            if cursor.isNull():
                break
            cursor.insertText(replace)
            count += 1
        cursor.endEditBlock()
        self._do_highlight(search, case_sensitive)
        self._editor.set_status_message(f'Replaced {count} occurrence(s)')
        return count

    # ── Internal helpers ─────────────────────────────────────────

    @staticmethod
    def _build_flags(case_sensitive: bool) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if case_sensitive:
            flags |= QTextDocument.FindCaseSensitively
        return flags

    def _do_highlight(self, query: str, case_sensitive: bool) -> None:
        if not query:
            self.clear_highlights()
            return
        content = self._editor.toPlainText()
        self._match_positions = SearchService.find_positions(content, query, case_sensitive)

        fmt = QTextCharFormat()
        fmt.setBackground(QColor(self._theme.get_colors()['find_match']))

        doc = self._editor.document()
        selections = []
        for pos in self._match_positions:
            cursor = QTextCursor(doc)
            cursor.setPosition(pos)
            cursor.movePosition(
                QTextCursor.MoveOperation.Right,
                QTextCursor.MoveMode.KeepAnchor,
                len(query),
            )
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = fmt
            selections.append(sel)

        self._editor.set_find_selections(selections)
        count = len(self._match_positions)
        if count == 0:
            self.match_count_updated.emit('0/0')
        else:
            self._emit_match_label(query)

    def _emit_match_label(self, query: str) -> None:
        total = len(self._match_positions)
        if not query or total == 0:
            self.match_count_updated.emit('0/0' if query else '')
            return
        cursor = self._editor.textCursor()
        pos = cursor.selectionStart() if cursor.hasSelection() else cursor.position()
        index = SearchService.match_index(self._match_positions, pos)
        if index is None:
            index = 0
        self.match_count_updated.emit(f'{index + 1}/{total}')
