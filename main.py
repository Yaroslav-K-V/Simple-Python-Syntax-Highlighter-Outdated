"""Main application window.

Entry point for PyGlow.  Creates a QMainWindow
with menu bar, status bar, code editor, find bar, and syntax
highlighting.  Supports open/save, find & replace, go-to-line,
theme switching, and a settings dialog.
"""
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox,
    QStatusBar, QLabel, QVBoxLayout, QWidget, QInputDialog, QToolButton,
)
from PySide6.QtGui import (
    QAction, QKeySequence, QFont, QShortcut, QTextCursor,
    QDragEnterEvent, QDropEvent,
)
from PySide6.QtCore import Slot

from config import Config
from theme import ThemeManager
from core.editor import CodeEditor
from highlighter import Highlighter
from find_bar import FindBar
from settings_dialog import SettingsDialog
try:
    from services.autocomplete_service import AutocompleteController
except ImportError:
    AutocompleteController = None


class MainWindow(QMainWindow):
    """Top-level application window.

    Owns the editor, find bar, highlighter, menus, and status bar.
    """

    def __init__(self) -> None:
        super().__init__()
        self._file: str | None = None   # Path to the currently open file
        self._unsaved = False            # True when the buffer has been modified

        # Load persistent settings and detect OS theme
        self._config = Config()
        self._theme = ThemeManager()
        self._base_font_size = self._config.font_size
        self._current_font_size = self._config.font_size

        # Override auto-detected theme if the user chose a fixed one
        if self._config.theme != 'auto':
            self._theme.set_theme(self._config.theme)

        # -- Central widget layout --
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Code editor (drops disabled so MainWindow receives file drags)
        self._editor = CodeEditor(self._theme, self)
        self._editor.setAcceptDrops(False)
        self._apply_font()
        self._editor.textChanged.connect(self._mark_unsaved)
        self._editor.cursorPositionChanged.connect(self._update_cursor)
        layout.addWidget(self._editor)

        # Find bar (hidden by default, shown via Ctrl+F)
        self._find_bar = FindBar(self._editor, self._theme, self)
        layout.addWidget(self._find_bar)

        self.setCentralWidget(container)

        # Syntax highlighter attached to the editor's document
        self._highlighter = Highlighter(self._editor.document(), self._theme)
        # LLM-based autocomplete controller (optional — works without torch)
        self._autocomplete = None
        if AutocompleteController is not None:
            try:
                self._autocomplete = AutocompleteController(self._editor, self._config)
                self._autocomplete.slow_mode_changed.connect(
                    self._on_llm_slow_mode
                )
            except Exception:
                pass

        # Build UI chrome
        self._setup_menus()
        self._setup_shortcuts()
        self._setup_status_bar()
        # Forward editor status messages to the status bar
        self._editor.status_message.connect(self.statusBar().showMessage)
        # Connect theme changes after all widgets exist
        self._theme.theme_changed.connect(self._apply_theme)
        self._apply_theme(self._theme.get_theme())
        self._update_title()
        self.resize(800, 600)
        self.setAcceptDrops(True)  # Allow drag & drop of files

    # ── Font ─────────────────────────────────────────────────────

    def _apply_font(self) -> None:
        """Set the editor font from config (family + size)."""
        font = QFont(self._config.font_family, self._current_font_size)
        self._editor.setFont(font)
        self._editor.refresh_metrics()
        self._update_font_label()

    # ── Menu bar ─────────────────────────────────────────────────

    @staticmethod
    def _add_action(menu, text, handler, shortcut=None) -> QAction:
        """Create a QAction, attach it to *menu*, and return it."""
        act = QAction(text, menu)
        if shortcut is not None:
            act.setShortcut(shortcut)
        act.triggered.connect(handler)
        menu.addAction(act)
        return act

    def _setup_menus(self) -> None:
        """Create File, Edit, and View menus with standard shortcuts."""
        menu = self.menuBar()

        # -- File menu --
        file_menu = menu.addMenu('&File')
        self._add_action(file_menu, '&New', self._new_file, QKeySequence.New)
        self._add_action(file_menu, '&Open...', self._open_file, QKeySequence.Open)
        self._add_action(file_menu, '&Save', self._save_file, QKeySequence.Save)
        self._add_action(file_menu, 'Save &As...', self._save_file_as, 'Ctrl+Shift+S')
        file_menu.addSeparator()
        self._add_action(file_menu, 'E&xit', self.close, QKeySequence.Quit)

        # -- Edit menu --
        edit_menu = menu.addMenu('&Edit')
        self._add_action(edit_menu, '&Undo', self._editor.undo, QKeySequence.Undo)
        self._add_action(edit_menu, '&Redo', self._editor.redo, QKeySequence.Redo)
        edit_menu.addSeparator()
        self._add_action(edit_menu, 'Cu&t', self._editor.cut, QKeySequence.Cut)
        self._add_action(edit_menu, '&Copy', self._editor.copy, QKeySequence.Copy)
        self._add_action(edit_menu, '&Paste', self._editor.paste, QKeySequence.Paste)
        edit_menu.addSeparator()
        self._add_action(edit_menu, '&Find...', self._show_find, QKeySequence.Find)
        self._add_action(edit_menu, '&Replace...', self._show_replace, 'Ctrl+H')
        self._add_action(edit_menu, '&Go to Line...', self._goto_line, 'Ctrl+G')
        edit_menu.addSeparator()
        self._add_action(edit_menu, 'Select &All', self._editor.selectAll, QKeySequence.SelectAll)

        # -- View menu --
        view_menu = menu.addMenu('&View')

        self._dark_act = QAction('&Dark Theme', self)
        self._dark_act.setCheckable(True)
        self._dark_act.triggered.connect(lambda: self._theme.set_theme('dark'))
        view_menu.addAction(self._dark_act)

        self._light_act = QAction('&Light Theme', self)
        self._light_act.setCheckable(True)
        self._light_act.triggered.connect(
            lambda: self._theme.set_theme('light')
        )
        view_menu.addAction(self._light_act)

        view_menu.addSeparator()
        self._add_action(view_menu, '&Settings...', self._show_settings)

        self._update_theme_checks()

    # ── Shortcuts ────────────────────────────────────────────────

    def _setup_shortcuts(self) -> None:
        """Register global keyboard shortcuts (F3, Shift+F3)."""
        QShortcut(QKeySequence('F3'), self, self._find_bar.find_next)
        QShortcut(QKeySequence('Shift+F3'), self, self._find_bar.find_prev)
        QShortcut(QKeySequence.ZoomIn, self, lambda: self._change_font_size(1))
        QShortcut(QKeySequence.ZoomOut, self, lambda: self._change_font_size(-1))
        QShortcut(QKeySequence('Ctrl+0'), self, self._reset_font_size)

    # ── Status bar ───────────────────────────────────────────────

    def _setup_status_bar(self) -> None:
        """Create status bar with cursor position, font size, encoding, and line count."""
        status = QStatusBar()
        self.setStatusBar(status)

        self._pos_label = QLabel('Ln 1, Col 1')       # Cursor position
        self._font_label = QLabel(f'Font {self._current_font_size}pt')  # Font size
        self._enc_label = QLabel('UTF-8')              # File encoding
        self._lines_label = QLabel('1 lines')          # Total line count
        self._llm_toggle = QToolButton()
        self._llm_toggle.setObjectName('llmToggle')
        self._llm_toggle.setCheckable(True)
        self._llm_toggle.setToolTip('Toggle LLM suggestions')
        self._llm_toggle.clicked.connect(self._toggle_llm)
        self._llm_slow = QLabel('Slow')
        self._llm_slow.setObjectName('llmSlow')
        self._llm_slow.hide()

        status.addPermanentWidget(self._pos_label)
        status.addPermanentWidget(self._font_label)
        status.addPermanentWidget(self._enc_label)
        status.addPermanentWidget(self._lines_label)
        status.addPermanentWidget(self._llm_toggle)
        status.addPermanentWidget(self._llm_slow)
        self._sync_llm_controls()

    def _sync_llm_controls(self) -> None:
        """Sync the LLM toggle + indicator with current settings."""
        if self._autocomplete is None:
            self._llm_toggle.setEnabled(False)
            self._llm_toggle.setChecked(False)
            self._llm_toggle.setText('LLM: N/A')
            self._llm_slow.hide()
            return
        ac_enabled = self._config.get('autocomplete', 'enabled')
        llm_enabled = self._config.get('autocomplete', 'llm_enabled')
        self._llm_toggle.setEnabled(ac_enabled)
        self._llm_toggle.setChecked(llm_enabled)
        self._llm_toggle.setText('LLM: On' if llm_enabled else 'LLM: Off')
        if not llm_enabled or not ac_enabled:
            self._llm_slow.hide()

    def _toggle_llm(self) -> None:
        """Toggle LLM suggestions from the status bar."""
        if self._autocomplete is None:
            return
        enabled = self._llm_toggle.isChecked()
        self._config.set('autocomplete', 'llm_enabled', enabled)
        self._config.save()
        self._sync_llm_controls()
        if self._autocomplete:
            self._autocomplete.refresh_settings()

    def _format_latency(self, ms: int) -> str:
        if ms >= 1000:
            return f"{ms / 1000:.1f}s"
        return f"{ms}ms"

    @Slot(bool, int)
    def _on_llm_slow_mode(self, slow: bool, latency_ms: int) -> None:
        """Show or hide the slow-mode indicator."""
        if not self._config.get('autocomplete', 'enabled'):
            self._llm_slow.hide()
            return
        if not self._config.get('autocomplete', 'llm_enabled'):
            self._llm_slow.hide()
            return
        if slow:
            self._llm_slow.setText(f"Slow {self._format_latency(latency_ms)}")
            self._llm_slow.show()
        else:
            self._llm_slow.hide()

    # ── Find & Replace & Go to Line ──────────────────────────────

    @Slot()
    def _show_find(self) -> None:
        """Show the find bar (Ctrl+F)."""
        self._find_bar.show_and_focus()

    @Slot()
    def _show_replace(self) -> None:
        """Show the find bar with replace row (Ctrl+H)."""
        self._find_bar.show_and_focus(show_replace=True)

    @Slot()
    def _goto_line(self) -> None:
        """Prompt the user for a line number and jump to it (Ctrl+G)."""
        max_line = self._editor.blockCount()
        line, ok = QInputDialog.getInt(
            self, 'Go to Line', f'Line number (1-{max_line}):',
            1, 1, max_line
        )
        if ok:
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock,
                                QTextCursor.MoveMode.MoveAnchor, line - 1)
            self._editor.setTextCursor(cursor)
            self._editor.centerCursor()  # Scroll so the line is visible
            self._editor.setFocus()

    # ── Settings ─────────────────────────────────────────────────

    @Slot()
    def _show_settings(self) -> None:
        """Open the settings dialog (View > Settings)."""
        dialog = SettingsDialog(self._config, self._theme, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    @Slot()
    def _on_settings_changed(self) -> None:
        """Re-apply font, theme, and autocomplete settings after changes."""
        self._base_font_size = self._config.font_size
        self._current_font_size = self._config.font_size
        self._apply_font()
        if self._config.theme != 'auto':
            self._theme.set_theme(self._config.theme)
        else:
            self._theme.refresh()  # Re-detect OS theme
        if self._autocomplete:
            self._autocomplete.reload_settings()
        self._sync_llm_controls()

    # ── Cursor / status updates ──────────────────────────────────

    @Slot()
    def _update_cursor(self) -> None:
        """Update status-bar labels when the cursor moves."""
        cursor = self._editor.textCursor()
        ln = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self._pos_label.setText(f'Ln {ln}, Col {col}')
        self._lines_label.setText(f'{self._editor.blockCount()} lines')

    def _update_font_label(self) -> None:
        """Refresh the font size readout in the status bar."""
        if hasattr(self, "_font_label"):
            self._font_label.setText(f'Font {self._current_font_size}pt')

    def _change_font_size(self, delta: int) -> None:
        """Increase or decrease editor font size."""
        new_size = max(6, min(72, self._current_font_size + delta))
        if new_size == self._current_font_size:
            return
        self._current_font_size = new_size
        self._apply_font()

    def _reset_font_size(self) -> None:
        """Reset editor font size to the configured base size."""
        if self._current_font_size == self._base_font_size:
            return
        self._current_font_size = self._base_font_size
        self._apply_font()

    # ── Theme ────────────────────────────────────────────────────

    @Slot(str)
    def _apply_theme(self, _: str) -> None:
        """Apply theme colors to the editor, menus, and status bar."""
        self._editor.apply_theme()
        self._update_theme_checks()
        colors = self._theme.get_colors()
        # Qt stylesheet for the window chrome
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {colors['editor_bg']}; }}
            QMenuBar {{
                background-color: {colors['gutter_bg']};
                color: {colors['editor_fg']};
            }}
            QMenuBar::item:selected {{
                background-color: {colors['selection']};
            }}
            QMenu {{
                background-color: {colors['gutter_bg']};
                color: {colors['editor_fg']};
            }}
            QMenu::item:selected {{
                background-color: {colors['selection']};
            }}
            QStatusBar {{
                background-color: {colors['gutter_bg']};
                color: {colors['line_number']};
            }}
            QLineEdit {{
                background-color: {colors['editor_bg']};
                color: {colors['editor_fg']};
                border: 1px solid {colors['line_number']};
            }}
            QPushButton {{
                background-color: {colors['gutter_bg']};
                color: {colors['editor_fg']};
                border: 1px solid {colors['line_number']};
                padding: 2px 8px;
            }}
            QPushButton:hover {{
                background-color: {colors['selection']};
            }}
            QCheckBox {{
                color: {colors['editor_fg']};
            }}
            QToolButton#llmToggle {{
                background-color: {colors['gutter_bg']};
                color: {colors['editor_fg']};
                border: 1px solid {colors['line_number']};
                padding: 2px 6px;
            }}
            QToolButton#llmToggle:checked {{
                background-color: {colors['selection']};
            }}
            QLabel#llmSlow {{
                color: {colors['accent']};
                padding: 0 4px;
            }}
        """)

    def _update_theme_checks(self) -> None:
        """Sync the View menu radio-style checkmarks with the active theme."""
        is_dark = self._theme.get_theme() == 'dark'
        self._dark_act.setChecked(is_dark)
        self._light_act.setChecked(not is_dark)

    # ── File I/O ─────────────────────────────────────────────────

    def _maybe_save_changes(self, message: str) -> bool:
        """Prompt to save unsaved changes.

        Returns True if it's safe to continue, False if the action should abort.
        """
        if not self._unsaved:
            return True
        reply = QMessageBox.question(
            self, 'Unsaved Changes',
            message,
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )
        if reply == QMessageBox.Save:
            return self._save_file()
        if reply == QMessageBox.Cancel:
            return False
        return True

    @Slot()
    def _new_file(self) -> None:
        """Clear the editor and start a new untitled buffer."""
        if not self._maybe_save_changes('Save changes before creating a new file?'):
            return
        self._editor.setPlainText("")
        self._file = None
        self._unsaved = False
        self._update_title()
        self._update_cursor()

    @Slot()
    def _open_file(self) -> None:
        """Show an Open dialog and load the selected file."""
        if not self._maybe_save_changes('Save changes before opening another file?'):
            return
        path, _ = QFileDialog.getOpenFileName(
            self, 'Open File', '', 'Python Files (*.py);;All Files (*)'
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str) -> None:
        """Read *path* into the editor, handling common I/O errors."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self._editor.setPlainText(f.read())
            self._file = path
            self._unsaved = False
            self._update_title()
            # Remember this file for next launch
            self._config.set('files', 'last_opened', path)
            self._config.save()
        except FileNotFoundError:
            QMessageBox.critical(self, 'Error', f'File not found: {path}')
        except PermissionError:
            QMessageBox.critical(self, 'Error', f'Permission denied: {path}')
        except UnicodeDecodeError:
            QMessageBox.critical(
                self, 'Error', f'Cannot decode file (not UTF-8): {path}'
            )
        except OSError as e:
            QMessageBox.critical(self, 'Error', f'Failed to read: {e}')

    @Slot()
    def _save_file(self) -> bool:
        """Save to the current path, or prompt Save As if untitled.

        Returns True on success, False on error or cancel.
        """
        if self._file:
            return self._write_file(self._file)
        return self._save_file_as()

    @Slot()
    def _save_file_as(self) -> bool:
        """Prompt for a new file path and save.

        Returns True on success, False on error or cancel.
        """
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save File', '', 'Python Files (*.py);;All Files (*)'
        )
        if path:
            return self._write_file(path)
        return False

    def _write_file(self, path: str) -> bool:
        """Write editor contents to *path*, optionally trimming whitespace.

        Returns True on success, False on I/O error.
        """
        try:
            text = self._editor.toPlainText()
            # Strip trailing whitespace per line if configured
            if self._config.trim_whitespace:
                lines = [line.rstrip() for line in text.split('\n')]
                text = '\n'.join(lines)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            self._file = path
            self._unsaved = False
            self._update_title()
            # Remember this file for next launch
            self._config.set('files', 'last_opened', path)
            self._config.save()
            return True
        except PermissionError:
            QMessageBox.critical(self, 'Error', f'Permission denied: {path}')
            return False
        except OSError as e:
            QMessageBox.critical(self, 'Error', f'Failed to save: {e}')
            return False

    # ── Window title ─────────────────────────────────────────────

    def _update_title(self) -> None:
        """Set the window title to 'filename* - PyGlow'."""
        name = os.path.basename(self._file) if self._file else 'Untitled'
        mod = '*' if self._unsaved else ''
        self.setWindowTitle(f'{name}{mod} - PyGlow')

    @Slot()
    def _mark_unsaved(self) -> None:
        """Flag the buffer as modified and update the title bar."""
        if not self._unsaved:
            self._unsaved = True
            self._update_title()

    # ── Drag & Drop ──────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept the drag if it contains file URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Open the first dropped file."""
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self._load_file(url.toLocalFile())
                break  # Open only the first file

    # ── Close handling ───────────────────────────────────────────

    def closeEvent(self, event) -> None:
        """Prompt to save unsaved changes before closing."""
        if not self._maybe_save_changes('Save changes before closing?'):
            event.ignore()
            return
        event.accept()


# ── Application entry point ──────────────────────────────────────

def main() -> None:
    """Create the QApplication, show the main window, and start the event loop."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # Open a file from CLI argument, or restore the last opened file
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        window._load_file(sys.argv[1])
    elif window._config.last_opened and os.path.isfile(window._config.last_opened):
        window._load_file(window._config.last_opened)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
