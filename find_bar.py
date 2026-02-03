"""Find toolbar widget."""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QCheckBox, QLabel,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QTextDocument, QTextCursor


class FindBar(QWidget):
    """Find toolbar for searching text in editor."""

    closed = Signal()

    def __init__(self, editor, parent=None) -> None:
        super().__init__(parent)
        self._editor = editor
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Search input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText('Find...')
        self._search_input.textChanged.connect(self._on_text_changed)
        self._search_input.returnPressed.connect(self.find_next)
        layout.addWidget(self._search_input)

        # Match count label
        self._count_label = QLabel('')
        layout.addWidget(self._count_label)

        # Case sensitivity
        self._case_check = QCheckBox('Aa')
        self._case_check.setToolTip('Match case')
        self._case_check.toggled.connect(self._on_text_changed)
        layout.addWidget(self._case_check)

        # Navigation buttons
        prev_btn = QPushButton('◀')
        prev_btn.setToolTip('Previous (Shift+F3)')
        prev_btn.setFixedWidth(30)
        prev_btn.clicked.connect(self.find_prev)
        layout.addWidget(prev_btn)

        next_btn = QPushButton('▶')
        next_btn.setToolTip('Next (F3)')
        next_btn.setFixedWidth(30)
        next_btn.clicked.connect(self.find_next)
        layout.addWidget(next_btn)

        # Close button
        close_btn = QPushButton('✕')
        close_btn.setFixedWidth(30)
        close_btn.clicked.connect(self._close)
        layout.addWidget(close_btn)

        # Shortcuts
        QShortcut(QKeySequence('Escape'), self, self._close)

    def show_and_focus(self) -> None:
        """Show the find bar and focus the input."""
        self.show()
        self._search_input.setFocus()
        self._search_input.selectAll()

    def _close(self) -> None:
        """Hide the find bar and clear highlights."""
        self.hide()
        self._clear_highlights()
        self._editor.setFocus()
        self.closed.emit()

    def _on_text_changed(self) -> None:
        """Handle search text change."""
        self._highlight_all()

    def _get_find_flags(self) -> QTextDocument.FindFlag:
        """Get find flags based on options."""
        flags = QTextDocument.FindFlag(0)
        if self._case_check.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        return flags

    def _highlight_all(self) -> None:
        """Highlight all matches in the editor."""
        self._clear_highlights()
        text = self._search_input.text()
        if not text:
            self._count_label.setText('')
            return

        # Count matches
        content = self._editor.toPlainText()
        if self._case_check.isChecked():
            count = content.count(text)
        else:
            count = content.lower().count(text.lower())

        self._count_label.setText(f'{count} matches')

        # Highlight using extra selections
        from PySide6.QtWidgets import QTextEdit
        from PySide6.QtGui import QColor, QTextCharFormat

        selections = []
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        fmt = QTextCharFormat()
        fmt.setBackground(QColor('#ffff00'))  # Yellow highlight

        doc = self._editor.document()
        flags = self._get_find_flags()

        while True:
            cursor = doc.find(text, cursor, flags)
            if cursor.isNull():
                break
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = fmt
            selections.append(sel)

        # Keep current line highlight and add search highlights
        current = self._editor.extraSelections()
        self._editor.setExtraSelections(current[:1] + selections)

    def _clear_highlights(self) -> None:
        """Clear search highlights, keep line highlight."""
        current = self._editor.extraSelections()
        self._editor.setExtraSelections(current[:1])

    def find_next(self) -> None:
        """Find next occurrence."""
        text = self._search_input.text()
        if not text:
            return
        flags = self._get_find_flags()
        if not self._editor.find(text, flags):
            # Wrap around
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self._editor.setTextCursor(cursor)
            self._editor.find(text, flags)

    def find_prev(self) -> None:
        """Find previous occurrence."""
        text = self._search_input.text()
        if not text:
            return
        flags = self._get_find_flags() | QTextDocument.FindBackward
        if not self._editor.find(text, flags):
            # Wrap around
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self._editor.setTextCursor(cursor)
            self._editor.find(text, flags)
