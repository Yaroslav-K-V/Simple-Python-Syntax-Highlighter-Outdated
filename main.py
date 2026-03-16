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
    QVBoxLayout, QWidget,
)
from PySide6.QtGui import (
    QAction, QKeySequence, QFont, QShortcut,
    QDragEnterEvent, QDropEvent,
)
from PySide6.QtCore import Slot

from config import Config
from theme import ThemeManager
from core.editor import CodeEditor
from highlighter import Highlighter
from find_bar import FindBar
from settings_dialog import SettingsDialog
from models.file_model import FileModel
from controllers.app_controller import AppController
from views.status_bar import StatusBarView
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

        # Load persistent settings and detect OS theme
        self._config = Config()
        self._theme = ThemeManager()
        self._file_model = FileModel(self._config)
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
        self._editor.textChanged.connect(self._file_model.mark_modified)
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
                self._autocomplete.suggestion_ready.connect(
                    self._editor.set_autocomplete_suggestion
                )
                self._autocomplete.autocomplete_cleared.connect(
                    self._editor.clear_autocomplete
                )
                self._autocomplete.status_updated.connect(
                    self.statusBar().showMessage
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
        # Wire FileModel signals
        self._file_model.content_ready.connect(self._editor.setPlainText)
        self._file_model.file_opened.connect(self._update_title)
        self._file_model.file_saved.connect(self._update_title)
        self._file_model.file_cleared.connect(self._update_title)
        self._file_model.unsaved_changed.connect(self._update_title)
        self._file_model.error_occurred.connect(
            lambda msg: QMessageBox.critical(self, 'Error', msg)
        )

        # Create AppController — owns coordination logic
        self._app_ctrl = AppController(
            window=self,
            editor=self._editor,
            file_model=self._file_model,
            config=self._config,
            theme=self._theme,
            find_bar=self._find_bar,
            autocomplete=self._autocomplete,
        )

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
        """Create the StatusBarView and wire its LLM toggle."""
        self._status_bar = StatusBarView(self)
        self.setStatusBar(self._status_bar)
        self._status_bar.update_font_size(self._current_font_size)
        self._status_bar.llm_toggled.connect(self._toggle_llm)

        # Expose sub-widgets for backward compat with AppController references
        self._pos_label = self._status_bar._pos_label
        self._font_label = self._status_bar._font_label
        self._lines_label = self._status_bar._lines_label
        self._llm_toggle = self._status_bar._llm_toggle
        self._llm_slow = self._status_bar._llm_slow

    def _sync_llm_controls(self) -> None:
        """Sync the LLM toggle + indicator with current settings."""
        available = self._autocomplete is not None
        if not available:
            self._status_bar.update_llm_state(False, False)
            return
        ac_enabled = self._config.get('autocomplete', 'enabled')
        llm_enabled = self._config.get('autocomplete', 'llm_enabled')
        self._status_bar.update_llm_state(llm_enabled, ac_enabled)

    def _toggle_llm(self, checked: bool) -> None:
        """Toggle LLM suggestions from the status bar."""
        if self._autocomplete is None:
            return
        self._config.set('autocomplete', 'llm_enabled', checked)
        self._config.save()
        self._sync_llm_controls()
        self._autocomplete.refresh_settings()

    def _format_latency(self, ms: int) -> str:
        if ms >= 1000:
            return f"{ms / 1000:.1f}s"
        return f"{ms}ms"

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
        """Delegate Go to Line to AppController."""
        self._app_ctrl.goto_line()

    # ── Settings ─────────────────────────────────────────────────

    @Slot()
    def _show_settings(self) -> None:
        """Open the settings dialog (View > Settings)."""
        dialog = SettingsDialog(self._config, self._theme, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    @Slot()
    def _on_settings_changed(self) -> None:
        """Delegate settings update to AppController."""
        self._app_ctrl.on_settings_changed()

    # ── Cursor / status updates ──────────────────────────────────

    def _update_font_label(self) -> None:
        """Refresh the font size readout in the status bar."""
        if hasattr(self, "_status_bar"):
            self._status_bar.update_font_size(self._current_font_size)

    def _change_font_size(self, delta: int) -> None:
        """Delegate font size change to AppController."""
        self._app_ctrl.change_font_size(delta)

    def _reset_font_size(self) -> None:
        """Delegate font size reset to AppController."""
        self._app_ctrl.reset_font_size()

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
        if not self._file_model.unsaved:
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
        self._file_model.clear()
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
        """Delegate file loading to FileModel."""
        self._file_model.load(path)

    @Slot()
    def _save_file(self) -> bool:
        """Save to the current path, or prompt Save As if untitled."""
        if self._file_model.path:
            return self._file_model.save(
                self._editor.toPlainText(),
                trim_whitespace=self._config.trim_whitespace,
            )
        return self._save_file_as()

    @Slot()
    def _save_file_as(self) -> bool:
        """Prompt for a new file path and save."""
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save File', '', 'Python Files (*.py);;All Files (*)'
        )
        if path:
            return self._file_model.save(
                self._editor.toPlainText(),
                path=path,
                trim_whitespace=self._config.trim_whitespace,
            )
        return False

    # ── Window title ─────────────────────────────────────────────

    @Slot()
    def _update_title(self, *_) -> None:
        """Set the window title to 'filename* - PyGlow'."""
        mod = '*' if self._file_model.unsaved else ''
        self.setWindowTitle(f'{self._file_model.display_name}{mod} - PyGlow')

    # ── Drag & Drop ──────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept the drag if it contains file URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Open the first dropped file."""
        if not self._maybe_save_changes('Save changes before opening dropped file?'):
            return
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
        window._file_model.load(sys.argv[1])
    elif window._config.last_opened and os.path.isfile(window._config.last_opened):
        window._file_model.load(window._config.last_opened)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
