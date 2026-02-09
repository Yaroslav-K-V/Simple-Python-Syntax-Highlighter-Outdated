"""Find toolbar widget.

Provides a horizontal search bar with:
- Text input with live match counting
- Case-sensitivity toggle
- Previous / Next navigation (Shift+F3 / F3)
- Yellow highlight on all matches via ExtraSelection
- Escape to close and clear highlights
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QCheckBox, QLabel,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QTextDocument, QTextCursor


class FindBar(QWidget):
    """Find toolbar for searching text in the editor.

    Signals:
        closed: Emitted when the bar is dismissed (Escape or close button).
    """

    closed = Signal()

    def __init__(self, editor, parent=None) -> None:
        super().__init__(parent)
        self._editor = editor  # Reference to the CodeEditor widget
        self._setup_ui()
        self.hide()  # Hidden by default; shown via Ctrl+F

    # ── UI construction ──────────────────────────────────────────

    def _setup_ui(self) -> None:
        """Build the search input, buttons, and shortcuts."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Search input field
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText('Find...')
        self._search_input.textChanged.connect(self._on_text_changed)
        self._search_input.returnPressed.connect(self.find_next)
        layout.addWidget(self._search_input)

        # Label showing the number of matches
        self._count_label = QLabel('')
        layout.addWidget(self._count_label)

        # Case sensitivity checkbox
        self._case_check = QCheckBox('Aa')
        self._case_check.setToolTip('Match case')
        self._case_check.toggled.connect(self._on_text_changed)
        layout.addWidget(self._case_check)

        # Previous match button
        prev_btn = QPushButton('\u25c0')  # ◀
        prev_btn.setToolTip('Previous (Shift+F3)')
        prev_btn.setFixedWidth(30)
        prev_btn.clicked.connect(self.find_prev)
        layout.addWidget(prev_btn)

        # Next match button
        next_btn = QPushButton('\u25b6')  # ▶
        next_btn.setToolTip('Next (F3)')
        next_btn.setFixedWidth(30)
        next_btn.clicked.connect(self.find_next)
        layout.addWidget(next_btn)

        # Close button
        close_btn = QPushButton('\u2715')  # ✕
        close_btn.setFixedWidth(30)
        close_btn.clicked.connect(self._close)
        layout.addWidget(close_btn)

        # Escape dismisses the bar
        QShortcut(QKeySequence('Escape'), self, self._close)

    # ── Show / hide ──────────────────────────────────────────────

    def show_and_focus(self) -> None:
        """Show the find bar and focus the search input."""
        self.show()
        self._search_input.setFocus()
        self._search_input.selectAll()

    def _close(self) -> None:
        """Hide the bar, clear highlights, and return focus to editor."""
        self.hide()
        self._clear_highlights()
        self._editor.setFocus()
        self.closed.emit()

    # ── Search logic ─────────────────────────────────────────────

    def _on_text_changed(self) -> None:
        """Re-highlight matches whenever the query or options change."""
        self._highlight_all()

    def _get_find_flags(self) -> QTextDocument.FindFlag:
        """Build Qt find flags from the current UI options."""
        flags = QTextDocument.FindFlag(0)
        if self._case_check.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        return flags

    def _highlight_all(self) -> None:
        """Highlight every match in the document using ExtraSelections."""
        self._clear_highlights()
        text = self._search_input.text()
        if not text:
            self._count_label.setText('')
            return

        # Count matches (simple string search)
        content = self._editor.toPlainText()
        if self._case_check.isChecked():
            count = content.count(text)
        else:
            count = content.lower().count(text.lower())

        self._count_label.setText(f'{count} matches')

        # Build ExtraSelection list with yellow background
        from PySide6.QtWidgets import QTextEdit
        from PySide6.QtGui import QColor, QTextCharFormat

        selections = []
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        fmt = QTextCharFormat()
        fmt.setBackground(QColor('#ffff00'))  # Yellow highlight

        doc = self._editor.document()
        flags = self._get_find_flags()

        # Walk through the document finding each occurrence
        while True:
            cursor = doc.find(text, cursor, flags)
            if cursor.isNull():
                break
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = fmt
            selections.append(sel)

        # Preserve the current-line highlight (index 0), append matches
        current = self._editor.extraSelections()
        self._editor.setExtraSelections(current[:1] + selections)

    def _clear_highlights(self) -> None:
        """Remove search highlights but keep the current-line highlight."""
        current = self._editor.extraSelections()
        self._editor.setExtraSelections(current[:1])

    # ── Navigation ───────────────────────────────────────────────

    def find_next(self) -> None:
        """Move the cursor to the next match (wraps around to top)."""
        text = self._search_input.text()
        if not text:
            return
        flags = self._get_find_flags()
        if not self._editor.find(text, flags):
            # No match found ahead -> wrap to document start
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self._editor.setTextCursor(cursor)
            self._editor.find(text, flags)

    def find_prev(self) -> None:
        """Move the cursor to the previous match (wraps around to end)."""
        text = self._search_input.text()
        if not text:
            return
        flags = self._get_find_flags() | QTextDocument.FindBackward
        if not self._editor.find(text, flags):
            # No match found behind -> wrap to document end
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self._editor.setTextCursor(cursor)
            self._editor.find(text, flags)
