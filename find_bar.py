"""Find & Replace toolbar widget.

Provides a horizontal search/replace bar with:
- Text input with live match counting
- Case-sensitivity toggle
- Previous / Next navigation (Shift+F3 / F3)
- Replace current match / Replace All
- Theme-colored highlight on all matches via ExtraSelection
- Escape to close and clear highlights
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QToolButton, QCheckBox,
    QLabel, QTextEdit, QStyle, QPushButton,
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import (
    QKeySequence, QShortcut, QTextDocument, QTextCursor, QColor,
    QTextCharFormat,
)

from services.search_service import SearchService


class FindBar(QWidget):
    """Find & Replace toolbar for searching and replacing text in the editor.

    Signals:
        closed: Emitted when the bar is dismissed (Escape or close button).
    """

    closed = Signal()

    def __init__(self, editor, theme_manager, parent=None) -> None:
        super().__init__(parent)
        self._editor = editor  # Reference to the CodeEditor widget
        self._theme = theme_manager
        self._theme.theme_changed.connect(self._apply_theme)
        self._match_positions: list[int] = []
        self._replace_visible = False
        self.setObjectName('findBar')
        self._setup_ui()
        self._apply_theme(self._theme.get_theme())
        self.hide()  # Hidden by default; shown via Ctrl+F

    # ── UI construction ──────────────────────────────────────────

    def _setup_ui(self) -> None:
        """Build the search/replace inputs, buttons, and shortcuts."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(4, 4, 4, 4)
        outer_layout.setSpacing(4)

        # ── Find row ──
        find_layout = QHBoxLayout()
        find_layout.setSpacing(6)

        # Search input field
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText('Find...')
        self._search_input.textChanged.connect(self._on_text_changed)
        self._search_input.returnPressed.connect(self.find_next)
        find_layout.addWidget(self._search_input)

        # Label showing the number of matches
        self._count_label = QLabel('')
        self._count_label.setObjectName('matchCount')
        self._count_label.setAlignment(Qt.AlignCenter)
        self._count_label.setMinimumWidth(52)
        find_layout.addWidget(self._count_label)

        # Case sensitivity checkbox
        self._case_check = QCheckBox('Aa')
        self._case_check.setToolTip('Match case')
        self._case_check.toggled.connect(self._on_text_changed)
        find_layout.addWidget(self._case_check)

        # Previous match button
        prev_btn = self._make_tool_button(
            QStyle.SP_ArrowBack, 'Previous (Shift+F3)', self.find_prev
        )
        find_layout.addWidget(prev_btn)

        # Next match button
        next_btn = self._make_tool_button(
            QStyle.SP_ArrowForward, 'Next (F3)', self.find_next
        )
        find_layout.addWidget(next_btn)

        # Close button
        close_btn = self._make_tool_button(
            QStyle.SP_DialogCloseButton, 'Close (Esc)', self._close
        )
        find_layout.addWidget(close_btn)

        outer_layout.addLayout(find_layout)

        # ── Replace row (hidden by default) ──
        self._replace_row = QWidget()
        replace_layout = QHBoxLayout(self._replace_row)
        replace_layout.setContentsMargins(0, 0, 0, 0)
        replace_layout.setSpacing(6)

        self._replace_input = QLineEdit()
        self._replace_input.setPlaceholderText('Replace...')
        self._replace_input.returnPressed.connect(self.replace_current)
        replace_layout.addWidget(self._replace_input)

        replace_btn = QPushButton('Replace')
        replace_btn.setToolTip('Replace current match')
        replace_btn.clicked.connect(self.replace_current)
        replace_layout.addWidget(replace_btn)

        replace_all_btn = QPushButton('Replace All')
        replace_all_btn.setToolTip('Replace all matches')
        replace_all_btn.clicked.connect(self.replace_all)
        replace_layout.addWidget(replace_all_btn)

        self._replace_row.hide()
        outer_layout.addWidget(self._replace_row)

        # Escape dismisses the bar
        QShortcut(QKeySequence('Escape'), self, self._close)

    def _make_tool_button(self, icon_style, tooltip, handler) -> QToolButton:
        """Create a small icon-only tool button for the find bar."""
        btn = QToolButton()
        btn.setIcon(self.style().standardIcon(icon_style))
        btn.setIconSize(QSize(14, 14))
        btn.setToolTip(tooltip)
        btn.setAutoRaise(True)
        btn.setFixedSize(26, 24)
        btn.clicked.connect(handler)
        return btn

    def _apply_theme(self, _: str) -> None:
        """Style the find bar to match the current theme."""
        colors = self._theme.get_colors()
        self.setStyleSheet(f"""
            QWidget#findBar {{
                background-color: {colors['gutter_bg']};
                border-top: 1px solid {colors['line_number']};
            }}
            QLineEdit {{
                background-color: {colors['editor_bg']};
                color: {colors['editor_fg']};
                border: 1px solid {colors['line_number']};
                padding: 2px 6px;
            }}
            QToolButton {{
                background-color: {colors['gutter_bg']};
                color: {colors['editor_fg']};
                border: 1px solid {colors['line_number']};
                border-radius: 2px;
            }}
            QToolButton:hover {{
                background-color: {colors['selection']};
            }}
            QPushButton {{
                background-color: {colors['gutter_bg']};
                color: {colors['editor_fg']};
                border: 1px solid {colors['line_number']};
                padding: 2px 8px;
                border-radius: 2px;
            }}
            QPushButton:hover {{
                background-color: {colors['selection']};
            }}
            QCheckBox {{
                color: {colors['editor_fg']};
            }}
            QLabel#matchCount {{
                color: {colors['accent']};
                font-weight: 600;
            }}
        """)
        if self._search_input.text():
            self._highlight_all()

    # ── Show / hide ──────────────────────────────────────────────

    def show_and_focus(self, show_replace: bool = False) -> None:
        """Show the find bar and focus the search input.

        Args:
            show_replace: If True, also show the replace row and focus
                the replace input.
        """
        self.show()
        if show_replace:
            self._replace_row.show()
            self._replace_visible = True
            self._replace_input.setFocus()
            self._replace_input.selectAll()
        else:
            self._search_input.setFocus()
            self._search_input.selectAll()
        if self._search_input.text():
            self._highlight_all()

    def _close(self) -> None:
        """Hide the bar, clear highlights, and return focus to editor."""
        self.hide()
        self._replace_row.hide()
        self._replace_visible = False
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

        content = self._editor.toPlainText()
        self._match_positions = SearchService.find_positions(
            content, text, self._case_check.isChecked()
        )
        count = len(self._match_positions)

        # Build ExtraSelection list with theme highlight
        selections = []

        fmt = QTextCharFormat()
        fmt.setBackground(QColor(self._theme.get_colors()['find_match']))

        doc = self._editor.document()
        for pos in self._match_positions:
            cursor = QTextCursor(doc)
            cursor.setPosition(pos)
            cursor.movePosition(
                QTextCursor.MoveOperation.Right,
                QTextCursor.MoveMode.KeepAnchor,
                len(text),
            )
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = fmt
            selections.append(sel)

        # Preserve the current-line highlight (index 0), append matches
        current = self._editor.extraSelections()
        self._editor.setExtraSelections(current[:1] + selections)
        if count == 0:
            self._count_label.setText('0/0')
        else:
            self._update_match_label()

    def _clear_highlights(self) -> None:
        """Remove search highlights but keep the current-line highlight."""
        current = self._editor.extraSelections()
        self._editor.setExtraSelections(current[:1])
        self._match_positions = []
        if not self._search_input.text():
            self._count_label.setText('')
        else:
            self._count_label.setText('0/0')

    def _update_match_label(self) -> None:
        """Update the X/Y match indicator based on cursor position."""
        total = len(self._match_positions)
        if not self._search_input.text():
            self._count_label.setText('')
            return
        if total == 0:
            self._count_label.setText('0/0')
            return
        cursor = self._editor.textCursor()
        pos = cursor.selectionStart() if cursor.hasSelection() else cursor.position()
        index = SearchService.match_index(self._match_positions, pos)
        if index is None:
            index = 0
        self._count_label.setText(f'{index + 1}/{total}')

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
        self._update_match_label()

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
        self._update_match_label()

    # ── Replace ──────────────────────────────────────────────────

    def replace_current(self) -> None:
        """Replace the current match and advance to the next one."""
        search_text = self._search_input.text()
        if not search_text:
            return

        cursor = self._editor.textCursor()
        if not cursor.hasSelection():
            self.find_next()
            return

        # Check if the current selection matches the search text
        selected = cursor.selectedText()
        case_sensitive = self._case_check.isChecked()
        if case_sensitive:
            match = selected == search_text
        else:
            match = selected.lower() == search_text.lower()

        if match:
            replace_text = self._replace_input.text()
            cursor.insertText(replace_text)
            self._highlight_all()

        self.find_next()

    def replace_all(self) -> None:
        """Replace all matches in the document as a single undo operation."""
        search_text = self._search_input.text()
        if not search_text:
            return

        replace_text = self._replace_input.text()
        flags = self._get_find_flags()
        doc = self._editor.document()

        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        count = 0
        cursor.beginEditBlock()
        while True:
            cursor = doc.find(search_text, cursor, flags)
            if cursor.isNull():
                break
            cursor.insertText(replace_text)
            count += 1
        cursor.endEditBlock()

        self._highlight_all()
        self._editor.set_status_message(f'Replaced {count} occurrence(s)')
