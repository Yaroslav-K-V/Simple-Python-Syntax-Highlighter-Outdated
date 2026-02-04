"""Code editor widget with line numbers, auto-indent, bracket matching."""
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit, QCompleter
from PySide6.QtCore import Qt, QRect, QSize, Slot, Signal, QStringListModel
from PySide6.QtGui import (
    QColor, QPainter, QTextFormat, QKeyEvent, QTextCharFormat, QTextCursor,
)


BRACKETS = {'(': ')', '[': ']', '{': '}'}
BRACKETS_CLOSE = {v: k for k, v in BRACKETS.items()}


class LineNumberArea(QWidget):
    """Line number gutter widget."""

    def __init__(self, editor: 'CodeEditor') -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """Plain text editor with line numbers and smart editing."""

    status_message = Signal(str)

    def __init__(self, theme_manager, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme_manager
        self._line_area = LineNumberArea(self)
        self._tab_size = 4
        self._use_spaces = True
        self._ghost_text = ""

        self._completion_model = QStringListModel(self)
        self._completer = QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setModel(self._completion_model)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitive)
        self._completer.activated.connect(self._insert_completion)

        self.blockCountChanged.connect(self._update_width)
        self.updateRequest.connect(self._update_area)
        self.cursorPositionChanged.connect(self._on_cursor_changed)

        self._update_width(0)
        self._highlight_current_line()

    def set_indent_settings(self, tab_size: int, use_spaces: bool) -> None:
        """Update indentation settings."""
        self._tab_size = tab_size
        self._use_spaces = use_spaces

    def line_number_width(self) -> int:
        """Calculate width for line numbers."""
        digits = max(3, len(str(self.blockCount())))
        return 8 + self.fontMetrics().horizontalAdvance('9') * digits

    @Slot(int)
    def _update_width(self, _: int) -> None:
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    @Slot(QRect, int)
    def _update_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(
                0, rect.y(), self._line_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_width(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_width(), cr.height())
        )

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._ghost_text:
            return
        painter = QPainter(self.viewport())
        colors = self._theme.get_colors()
        painter.setPen(QColor(colors.get("ghost_text", "#8a8a8a")))
        cursor_rect = self.cursorRect()
        metrics = self.fontMetrics()
        x = cursor_rect.x()
        y = cursor_rect.y() + metrics.ascent()
        ghost = self._ghost_text.splitlines()[0]
        painter.drawText(x, y, ghost)

    def paint_line_numbers(self, event) -> None:
        """Paint line numbers in gutter."""
        painter = QPainter(self._line_area)
        colors = self._theme.get_colors()
        painter.fillRect(event.rect(), QColor(colors['gutter_bg']))
        painter.setPen(QColor(colors['line_number']))

        block = self.firstVisibleBlock()
        num = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset()).top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())
        height = self.fontMetrics().height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0, top, self._line_area.width() - 4, height,
                    Qt.AlignRight, str(num + 1)
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            num += 1

    @Slot()
    def _on_cursor_changed(self) -> None:
        """Handle cursor position change."""
        self._highlight_current_line()
        self._highlight_matching_bracket()

    def _highlight_current_line(self) -> None:
        """Highlight current line."""
        if self.isReadOnly():
            return
        selections = []

        # Current line highlight
        selection = QTextEdit.ExtraSelection()
        color = QColor(self._theme.get_colors()['current_line'])
        selection.format.setBackground(color)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        selections.append(selection)

        self.setExtraSelections(selections)

    def _highlight_matching_bracket(self) -> None:
        """Highlight matching bracket if cursor is near one."""
        cursor = self.textCursor()
        pos = cursor.position()
        doc = self.document()
        text = doc.toPlainText()

        if pos >= len(text):
            return

        char = text[pos] if pos < len(text) else ''
        prev_char = text[pos - 1] if pos > 0 else ''

        # Check if cursor is next to a bracket
        bracket_pos = -1
        bracket_char = ''

        if char in BRACKETS or char in BRACKETS_CLOSE:
            bracket_pos = pos
            bracket_char = char
        elif prev_char in BRACKETS or prev_char in BRACKETS_CLOSE:
            bracket_pos = pos - 1
            bracket_char = prev_char

        if bracket_pos < 0:
            return

        # Find matching bracket
        match_pos = self._find_matching_bracket(text, bracket_pos, bracket_char)
        if match_pos < 0:
            return

        # Add bracket highlights to existing selections
        selections = self.extraSelections()

        fmt = QTextCharFormat()
        fmt.setBackground(QColor('#ffff00' if self._theme.get_theme() == 'light'
                                  else '#3a3a00'))

        for p in [bracket_pos, match_pos]:
            sel = QTextEdit.ExtraSelection()
            sel.format = fmt
            c = self.textCursor()
            c.setPosition(p)
            c.movePosition(QTextCursor.MoveOperation.Right,
                          QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = c
            selections.append(sel)

        self.setExtraSelections(selections)

    def _find_matching_bracket(self, text: str, pos: int, char: str) -> int:
        """Find position of matching bracket."""
        if char in BRACKETS:
            # Search forward
            target = BRACKETS[char]
            direction = 1
            start = pos + 1
            end = len(text)
        else:
            # Search backward
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

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press with auto-indent."""
        if self._ghost_text:
            if event.key() == Qt.Key_Tab:
                self._accept_autocomplete()
                return
            if event.key() == Qt.Key_Escape:
                self.clear_autocomplete()
                return
            if event.key() in (
                Qt.Key_Backspace,
                Qt.Key_Delete,
                Qt.Key_Return,
                Qt.Key_Enter,
            ) or event.text():
                self.clear_autocomplete()

        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._handle_newline()
            return

        if event.key() == Qt.Key_Tab:
            self._handle_tab()
            return

        if event.key() == Qt.Key_Backtab:
            self._handle_backtab()
            return

        super().keyPressEvent(event)

    def _handle_newline(self) -> None:
        """Handle Enter key with auto-indent."""
        cursor = self.textCursor()
        block = cursor.block()
        line = block.text()

        # Calculate current indent
        indent = ''
        for c in line:
            if c in ' \t':
                indent += c
            else:
                break

        # Check if line ends with colon (increase indent)
        stripped = line.rstrip()
        if stripped.endswith(':'):
            if self._use_spaces:
                indent += ' ' * self._tab_size
            else:
                indent += '\t'

        # Insert newline and indent
        cursor.insertText('\n' + indent)
        self.setTextCursor(cursor)

    def _handle_tab(self) -> None:
        """Handle Tab key."""
        cursor = self.textCursor()
        if self._use_spaces:
            cursor.insertText(' ' * self._tab_size)
        else:
            cursor.insertText('\t')

    def _handle_backtab(self) -> None:
        """Handle Shift+Tab to decrease indent."""
        cursor = self.textCursor()
        block = cursor.block()
        line = block.text()

        # Find indent to remove
        remove = 0
        for i, c in enumerate(line):
            if c == ' ':
                remove += 1
                if remove >= self._tab_size:
                    break
            elif c == '\t':
                remove = 1
                break
            else:
                break

        if remove > 0:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            for _ in range(remove):
                cursor.deleteChar()

    def _insert_completion(self, text: str) -> None:
        if not text:
            return
        cursor = self.textCursor()
        cursor.insertText(text)
        self.setTextCursor(cursor)
        self.clear_autocomplete()

    def _accept_autocomplete(self) -> None:
        if not self._ghost_text:
            return
        self._insert_completion(self._ghost_text)

    def set_autocomplete_suggestion(self, text: str) -> None:
        self._ghost_text = text
        self.viewport().update()
        if text:
            self._completion_model.setStringList([text])
            self._completer.setCompletionPrefix("")
            self._completer.complete(self.cursorRect())
        else:
            self._completer.popup().hide()

    def clear_autocomplete(self) -> None:
        if not self._ghost_text:
            return
        self._ghost_text = ""
        self.viewport().update()
        self._completer.popup().hide()

    def set_status_message(self, message: str) -> None:
        self.status_message.emit(message)

    def apply_theme(self) -> None:
        """Apply current theme colors."""
        colors = self._theme.get_colors()
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {colors['editor_bg']};
                color: {colors['editor_fg']};
                selection-background-color: {colors['selection']};
            }}
        """)
        self._highlight_current_line()
        self._line_area.update()
