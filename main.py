"""Main application window.

Entry point for PyGlow.  Creates a QMainWindow
with menu bar, status bar, code editor, find bar, and syntax
highlighting.  Supports open/save, find & go-to-line, theme switching,
and a settings dialog.
"""
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox,
    QStatusBar, QLabel, QVBoxLayout, QWidget, QInputDialog,
)
from PySide6.QtGui import (
    QAction, QKeySequence, QFont, QShortcut, QTextCursor,
    QDragEnterEvent, QDropEvent,
)
from PySide6.QtCore import Slot, QUrl

from config import Config
from theme import ThemeManager
from code_editor import CodeEditor
from highlighter import Highlighter
from find_bar import FindBar
from settings_dialog import SettingsDialog
try:
    from autocomplete import AutocompleteController
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
        self._theme.theme_changed.connect(self._apply_theme)

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
        self._find_bar = FindBar(self._editor, self)
        layout.addWidget(self._find_bar)

        self.setCentralWidget(container)

        # Syntax highlighter attached to the editor's document
        self._highlighter = Highlighter(self._editor.document(), self._theme)
        # LLM-based autocomplete controller (optional — works without torch)
        self._autocomplete = None
        if AutocompleteController is not None:
            try:
                self._autocomplete = AutocompleteController(self._editor, self._config)
            except Exception:
                pass

        # Build UI chrome
        self._setup_menus()
        self._setup_shortcuts()
        self._setup_status_bar()
        # Forward editor status messages to the status bar
        self._editor.status_message.connect(self.statusBar().showMessage)
        self._apply_theme(self._theme.get_theme())
        self._update_title()
        self.resize(800, 600)
        self.setAcceptDrops(True)  # Allow drag & drop of files

    # ── Font ─────────────────────────────────────────────────────

    def _apply_font(self) -> None:
        """Set the editor font from config (family + size)."""
        font = QFont(self._config.font_family, self._config.font_size)
        self._editor.setFont(font)

    # ── Menu bar ─────────────────────────────────────────────────

    def _setup_menus(self) -> None:
        """Create File, Edit, and View menus with standard shortcuts."""
        menu = self.menuBar()

        # -- File menu --
        file_menu = menu.addMenu('&File')

        open_act = QAction('&Open...', self)
        open_act.setShortcut(QKeySequence.Open)
        open_act.triggered.connect(self._open_file)
        file_menu.addAction(open_act)

        save_act = QAction('&Save', self)
        save_act.setShortcut(QKeySequence.Save)
        save_act.triggered.connect(self._save_file)
        file_menu.addAction(save_act)

        save_as_act = QAction('Save &As...', self)
        save_as_act.setShortcut('Ctrl+Shift+S')
        save_as_act.triggered.connect(self._save_file_as)
        file_menu.addAction(save_as_act)

        file_menu.addSeparator()

        exit_act = QAction('E&xit', self)
        exit_act.setShortcut(QKeySequence.Quit)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # -- Edit menu --
        edit_menu = menu.addMenu('&Edit')

        undo_act = QAction('&Undo', self)
        undo_act.setShortcut(QKeySequence.Undo)
        undo_act.triggered.connect(self._editor.undo)
        edit_menu.addAction(undo_act)

        redo_act = QAction('&Redo', self)
        redo_act.setShortcut(QKeySequence.Redo)
        redo_act.triggered.connect(self._editor.redo)
        edit_menu.addAction(redo_act)

        edit_menu.addSeparator()

        cut_act = QAction('Cu&t', self)
        cut_act.setShortcut(QKeySequence.Cut)
        cut_act.triggered.connect(self._editor.cut)
        edit_menu.addAction(cut_act)

        copy_act = QAction('&Copy', self)
        copy_act.setShortcut(QKeySequence.Copy)
        copy_act.triggered.connect(self._editor.copy)
        edit_menu.addAction(copy_act)

        paste_act = QAction('&Paste', self)
        paste_act.setShortcut(QKeySequence.Paste)
        paste_act.triggered.connect(self._editor.paste)
        edit_menu.addAction(paste_act)

        edit_menu.addSeparator()

        find_act = QAction('&Find...', self)
        find_act.setShortcut(QKeySequence.Find)
        find_act.triggered.connect(self._show_find)
        edit_menu.addAction(find_act)

        goto_act = QAction('&Go to Line...', self)
        goto_act.setShortcut('Ctrl+G')
        goto_act.triggered.connect(self._goto_line)
        edit_menu.addAction(goto_act)

        edit_menu.addSeparator()

        select_all_act = QAction('Select &All', self)
        select_all_act.setShortcut(QKeySequence.SelectAll)
        select_all_act.triggered.connect(self._editor.selectAll)
        edit_menu.addAction(select_all_act)

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

        settings_act = QAction('&Settings...', self)
        settings_act.triggered.connect(self._show_settings)
        view_menu.addAction(settings_act)

        self._update_theme_checks()

    # ── Shortcuts ────────────────────────────────────────────────

    def _setup_shortcuts(self) -> None:
        """Register global keyboard shortcuts (F3, Shift+F3)."""
        QShortcut(QKeySequence('F3'), self, self._find_bar.find_next)
        QShortcut(QKeySequence('Shift+F3'), self, self._find_bar.find_prev)

    # ── Status bar ───────────────────────────────────────────────

    def _setup_status_bar(self) -> None:
        """Create status bar with cursor position, encoding, and line count."""
        status = QStatusBar()
        self.setStatusBar(status)

        self._pos_label = QLabel('Ln 1, Col 1')       # Cursor position
        self._enc_label = QLabel('UTF-8')              # File encoding
        self._lines_label = QLabel('1 lines')          # Total line count

        status.addPermanentWidget(self._pos_label)
        status.addPermanentWidget(self._enc_label)
        status.addPermanentWidget(self._lines_label)

    # ── Find & Go to Line ────────────────────────────────────────

    @Slot()
    def _show_find(self) -> None:
        """Show the find bar (Ctrl+F)."""
        self._find_bar.show_and_focus()

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
        self._apply_font()
        if self._config.theme != 'auto':
            self._theme.set_theme(self._config.theme)
        else:
            self._theme.refresh()  # Re-detect OS theme
        if self._autocomplete:
            self._autocomplete.reload_settings()

    # ── Cursor / status updates ──────────────────────────────────

    @Slot()
    def _update_cursor(self) -> None:
        """Update status-bar labels when the cursor moves."""
        cursor = self._editor.textCursor()
        ln = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self._pos_label.setText(f'Ln {ln}, Col {col}')
        self._lines_label.setText(f'{self._editor.blockCount()} lines')

    # ── Theme ────────────────────────────────────────────────────

    @Slot(str)
    def _apply_theme(self, _: str) -> None:
        """Apply theme colors to the editor, menus, and status bar."""
        if not hasattr(self, "_editor"):
            return  # Guard during __init__ before editor exists
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
        """)

    def _update_theme_checks(self) -> None:
        """Sync the View menu radio-style checkmarks with the active theme."""
        is_dark = self._theme.get_theme() == 'dark'
        self._dark_act.setChecked(is_dark)
        self._light_act.setChecked(not is_dark)

    # ── File I/O ─────────────────────────────────────────────────

    @Slot()
    def _open_file(self) -> None:
        """Show an Open dialog and load the selected file."""
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
        if self._unsaved:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                'Save changes before closing?',
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self._save_file()
                if self._unsaved:  # Save was cancelled
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
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
