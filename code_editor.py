"""Code editor widget with line numbers, auto-indent, bracket matching.

Provides a QPlainTextEdit-based editor with:
- Line number gutter (LineNumberArea)
- Current line highlighting
- Bracket matching for (), [], {}
- Auto-indent on Enter (copies indent, adds level after ':')
- Tab / Shift+Tab handling with spaces or tabs
- Ghost-text autocomplete overlay
"""
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit, QCompleter
from PySide6.QtCore import Qt, QRect, QSize, Slot, Signal, QStringListModel
from PySide6.QtGui import (
    QColor, QPainter, QTextFormat, QKeyEvent, QTextCharFormat, QTextCursor,
)

# Maps open brackets to their close counterparts
BRACKETS = {'(': ')', '[': ']', '{': '}'}
# Reverse map: close bracket -> open bracket
BRACKETS_CLOSE = {v: k for k, v in BRACKETS.items()}
# Auto-close pairs: typing the key inserts both key + value
AUTO_CLOSE = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}


class LineNumberArea(QWidget):
    """Gutter widget that draws line numbers beside the editor.

    Delegates all painting back to the parent CodeEditor so it can
    align numbers with the corresponding text blocks.
    """

    def __init__(self, editor: 'CodeEditor') -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        """Return preferred width based on digit count."""
        return QSize(self._editor.line_number_width(), 0)

    def paintEvent(self, event) -> None:
        """Forward paint event to the editor's line-number renderer."""
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """Plain text editor with line numbers and smart editing features.

    Signals:
        status_message(str): Emitted to display a message in the status bar.
    """

    status_message = Signal(str)

    def __init__(self, theme_manager, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme_manager
        self._line_area = LineNumberArea(self)
        self._tab_size = 4          # Number of spaces per indent level
        self._use_spaces = True     # True = spaces, False = real tabs
        self._ghost_text = ""       # Autocomplete suggestion shown as overlay

        # --- Inline completer (popup list) ---
        self._completion_model = QStringListModel(self)
        self._completer = QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setModel(self._completion_model)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitive)
        self._completer.activated.connect(self._insert_completion)

        # Connect editor signals for live updates
        self.blockCountChanged.connect(self._update_width)       # Re-calc gutter width on line count change
        self.updateRequest.connect(self._update_area)            # Scroll / repaint gutter
        self.cursorPositionChanged.connect(self._on_cursor_changed)  # Highlight line & brackets

        self._update_width(0)
        self._highlight_current_line()

    # ── Indentation settings ─────────────────────────────────────

    def set_indent_settings(self, tab_size: int, use_spaces: bool) -> None:
        """Update indentation preferences (called from Settings dialog)."""
        self._tab_size = tab_size
        self._use_spaces = use_spaces

    # ── Line-number gutter ───────────────────────────────────────

    def line_number_width(self) -> int:
        """Calculate pixel width required for the line-number gutter.

        Reserves space for at least 3 digits and adds 8 px padding.
        """
        digits = max(3, len(str(self.blockCount())))
        return 8 + self.fontMetrics().horizontalAdvance('9') * digits

    @Slot(int)
    def _update_width(self, _: int) -> None:
        """Adjust left viewport margin to make room for the gutter."""
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    @Slot(QRect, int)
    def _update_area(self, rect: QRect, dy: int) -> None:
        """Scroll or repaint the gutter in sync with the editor viewport."""
        if dy:
            self._line_area.scroll(0, dy)  # Vertical scroll
        else:
            self._line_area.update(
                0, rect.y(), self._line_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_width(0)

    def resizeEvent(self, event) -> None:
        """Resize the gutter to match the editor's content area."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_width(), cr.height())
        )

    def paintEvent(self, event) -> None:
        """Draw the editor content, then overlay ghost-text if present."""
        super().paintEvent(event)
        if not self._ghost_text:
            return
        # Draw semi-transparent autocomplete suggestion at the cursor
        painter = QPainter(self.viewport())
        colors = self._theme.get_colors()
        painter.setPen(QColor(colors.get("ghost_text", "#8a8a8a")))
        cursor_rect = self.cursorRect()
        metrics = self.fontMetrics()
        x = cursor_rect.x()
        y = cursor_rect.y() + metrics.ascent()
        ghost = self._ghost_text.splitlines()[0]  # Only show first line
        painter.drawText(x, y, ghost)

    def paint_line_numbers(self, event) -> None:
        """Paint right-aligned line numbers inside the gutter area."""
        painter = QPainter(self._line_area)
        colors = self._theme.get_colors()
        painter.fillRect(event.rect(), QColor(colors['gutter_bg']))
        painter.setPen(QColor(colors['line_number']))

        block = self.firstVisibleBlock()
        num = block.blockNumber()
        # Top pixel of the first visible block
        top = int(
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset()).top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())
        height = self.fontMetrics().height()

        # Walk visible blocks and draw their line numbers
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

    # ── Cursor change handling ───────────────────────────────────

    @Slot()
    def _on_cursor_changed(self) -> None:
        """React to cursor movement: re-highlight line and brackets."""
        self._highlight_current_line()
        self._highlight_matching_bracket()

    def _highlight_current_line(self) -> None:
        """Apply a full-width background color to the current line."""
        if self.isReadOnly():
            return
        selections = []
        selection = QTextEdit.ExtraSelection()
        color = QColor(self._theme.get_colors()['current_line'])
        selection.format.setBackground(color)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        selections.append(selection)
        self.setExtraSelections(selections)

    # ── Bracket matching ─────────────────────────────────────────

    def _highlight_matching_bracket(self) -> None:
        """Find and highlight the matching bracket near the cursor."""
        cursor = self.textCursor()
        pos = cursor.position()
        doc = self.document()
        text = doc.toPlainText()

        if pos >= len(text):
            return

        char = text[pos] if pos < len(text) else ''
        prev_char = text[pos - 1] if pos > 0 else ''

        # Determine which bracket character is adjacent to the cursor
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

        # Search for the matching bracket using depth tracking
        match_pos = self._find_matching_bracket(text, bracket_pos, bracket_char)
        if match_pos < 0:
            return

        # Add highlight selections for both brackets
        selections = self.extraSelections()
        fmt = QTextCharFormat()
        fmt.setBackground(self._theme.get_color('bracket_match'))

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
        """Find the position of the matching bracket using depth counting.

        Args:
            text:  Full document text.
            pos:   Position of the bracket to match.
            char:  The bracket character at *pos*.

        Returns:
            Index of the matching bracket, or -1 if not found.
        """
        if char in BRACKETS:
            # Opening bracket -> search forward
            target = BRACKETS[char]
            direction = 1
            start = pos + 1
            end = len(text)
        else:
            # Closing bracket -> search backward
            target = BRACKETS_CLOSE[char]
            direction = -1
            start = pos - 1
            end = -1

        depth = 1
        i = start
        while i != end:
            c = text[i]
            if c == char:
                depth += 1      # Nested bracket of same type
            elif c == target:
                depth -= 1
                if depth == 0:
                    return i    # Found the match
            i += direction

        return -1  # No matching bracket found

    # ── Key handling ─────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key presses: autocomplete accept/dismiss, auto-indent, tab."""
        # --- Autocomplete interaction ---
        if self._ghost_text:
            if event.key() == Qt.Key_Tab:
                self._accept_autocomplete()  # Tab accepts the suggestion
                return
            if event.key() == Qt.Key_Escape:
                self.clear_autocomplete()    # Escape dismisses
                return
            # Any other typing clears the ghost text
            if event.key() in (
                Qt.Key_Backspace,
                Qt.Key_Delete,
                Qt.Key_Return,
                Qt.Key_Enter,
            ) or event.text():
                self.clear_autocomplete()

        # --- Auto-indent on Enter ---
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._handle_newline()
            return

        # --- Tab / Shift+Tab indent ---
        if event.key() == Qt.Key_Tab:
            self._handle_tab()
            return

        if event.key() == Qt.Key_Backtab:
            self._handle_backtab()
            return

        # --- Ctrl+D: duplicate current line ---
        if event.key() == Qt.Key_D and event.modifiers() == Qt.ControlModifier:
            self._duplicate_line()
            return

        # --- Auto-close brackets and quotes ---
        ch = event.text()
        if ch in AUTO_CLOSE:
            cursor = self.textCursor()
            closing = AUTO_CLOSE[ch]
            # For quotes, skip auto-close if already inside the same quote
            if ch in ('"', "'"):
                line = cursor.block().text()
                col = cursor.columnNumber()
                # Count how many of this quote appear before the cursor
                if line[:col].count(ch) % 2 == 1:
                    super().keyPressEvent(event)
                    return
            # If next char is already the closing char, just move past it
            pos = cursor.position()
            text = self.document().toPlainText()
            if pos < len(text) and text[pos] == closing and ch == closing:
                cursor.movePosition(QTextCursor.MoveOperation.Right)
                self.setTextCursor(cursor)
                return
            # Insert pair and place cursor between them
            cursor.insertText(ch + closing)
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            return

        # --- Skip over closing bracket if typed manually ---
        if ch in BRACKETS_CLOSE or ch in ('"', "'"):
            cursor = self.textCursor()
            pos = cursor.position()
            text = self.document().toPlainText()
            if pos < len(text) and text[pos] == ch:
                cursor.movePosition(QTextCursor.MoveOperation.Right)
                self.setTextCursor(cursor)
                return

        super().keyPressEvent(event)

    def _handle_newline(self) -> None:
        """Insert a newline and copy the current line's indentation.

        If the line ends with ':', adds one extra indent level
        (spaces or tab, depending on settings).
        """
        cursor = self.textCursor()
        block = cursor.block()
        line = block.text()

        # Copy leading whitespace from the current line
        indent = ''
        for c in line:
            if c in ' \t':
                indent += c
            else:
                break

        # Increase indent after a colon (e.g. def, if, for, class)
        stripped = line.rstrip()
        if stripped.endswith(':'):
            if self._use_spaces:
                indent += ' ' * self._tab_size
            else:
                indent += '\t'

        cursor.insertText('\n' + indent)
        self.setTextCursor(cursor)

    def _handle_tab(self) -> None:
        """Insert indentation: spaces or a real tab character."""
        cursor = self.textCursor()
        if self._use_spaces:
            cursor.insertText(' ' * self._tab_size)
        else:
            cursor.insertText('\t')

    def _duplicate_line(self) -> None:
        """Duplicate the current line (Ctrl+D)."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                            QTextCursor.MoveMode.KeepAnchor)
        line_text = cursor.selectedText()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        cursor.insertText('\n' + line_text)

    def _handle_backtab(self) -> None:
        """Remove one indent level from the start of the current line."""
        cursor = self.textCursor()
        block = cursor.block()
        line = block.text()

        # Count how many whitespace chars to remove (up to tab_size)
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

    # ── Autocomplete helpers ─────────────────────────────────────

    def _insert_completion(self, text: str) -> None:
        """Insert the chosen completion text at the cursor."""
        if not text:
            return
        cursor = self.textCursor()
        cursor.insertText(text)
        self.setTextCursor(cursor)
        self.clear_autocomplete()

    def _accept_autocomplete(self) -> None:
        """Accept the current ghost-text suggestion."""
        if not self._ghost_text:
            return
        self._insert_completion(self._ghost_text)

    def set_autocomplete_suggestion(self, text: str) -> None:
        """Show *text* as a ghost-text suggestion and open the popup."""
        self._ghost_text = text
        self.viewport().update()  # Trigger repaint to draw ghost text
        if text:
            self._completion_model.setStringList([text])
            self._completer.setCompletionPrefix("")
            self._completer.complete(self.cursorRect())
        else:
            self._completer.popup().hide()

    def clear_autocomplete(self) -> None:
        """Remove ghost-text overlay and hide the popup."""
        if not self._ghost_text:
            return
        self._ghost_text = ""
        self.viewport().update()
        self._completer.popup().hide()

    # ── Status & theme ───────────────────────────────────────────

    def set_status_message(self, message: str) -> None:
        """Emit a status-bar message (forwarded to MainWindow)."""
        self.status_message.emit(message)

    def apply_theme(self) -> None:
        """Apply current theme colors to the editor and gutter."""
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

    def refresh_metrics(self) -> None:
        """Recalculate gutter width after font or layout changes."""
        self._update_width(0)
        self._line_area.update()
