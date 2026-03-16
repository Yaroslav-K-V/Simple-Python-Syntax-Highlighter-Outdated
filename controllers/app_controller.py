"""Application controller — wires all signal/slot connections.

Owns the top-level coordination logic  so that MainWindow can
remain a pure View with no program logic.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QInputDialog


class AppController(QObject):
    """Coordinates MainWindow (View), FileModel, and all services.

    All signal ↔ slot wiring lives in __init__ so the topology of
    the whole application is visible in one place.
    """

    def __init__(
        self,
        window,        # MainWindow
        editor,        # CodeEditor
        file_model,    # FileModel
        config,        # Config
        theme,         # ThemeManager
        find_bar,      # FindBar
        autocomplete,  # AutocompleteController | None
    ) -> None:
        super().__init__(window)
        self._window = window
        self._editor = editor
        self._file_model = file_model
        self._config = config
        self._theme = theme
        self._find_bar = find_bar
        self._autocomplete = autocomplete

        self._wire_signals()

    # ── Signal wiring ─────────────────────────────────────────────

    def _wire_signals(self) -> None:
        """Connect all signals to slots."""
        # Settings dialog
        # (MainWindow._show_settings creates dialog and connects settings_changed)
        # — handled in MainWindow for now; AppController handles the response.

        # Autocomplete slow-mode indicator
        if self._autocomplete is not None:
            self._autocomplete.slow_mode_changed.connect(self._on_llm_slow_mode)

        # Cursor updates → status bar
        self._editor.cursorPositionChanged.connect(self._update_cursor)

    # ── Settings ─────────────────────────────────────────────────

    @Slot()
    def on_settings_changed(self) -> None:
        """Re-apply font, theme, and autocomplete settings."""
        self._window._base_font_size = self._config.font_size
        self._window._current_font_size = self._config.font_size
        self._window._apply_font()
        if self._config.theme != 'auto':
            self._theme.set_theme(self._config.theme)
        else:
            self._theme.refresh()
        if self._autocomplete:
            self._autocomplete.reload_settings()
        self._window._sync_llm_controls()

    # ── Font ─────────────────────────────────────────────────────

    def change_font_size(self, delta: int) -> None:
        w = self._window
        new_size = max(6, min(72, w._current_font_size + delta))
        if new_size == w._current_font_size:
            return
        w._current_font_size = new_size
        w._apply_font()

    def reset_font_size(self) -> None:
        w = self._window
        if w._current_font_size == w._base_font_size:
            return
        w._current_font_size = w._base_font_size
        w._apply_font()

    # ── Go to Line ───────────────────────────────────────────────

    @Slot()
    def goto_line(self) -> None:
        max_line = self._editor.blockCount()
        line, ok = QInputDialog.getInt(
            self._window, 'Go to Line', f'Line number (1-{max_line}):',
            1, 1, max_line
        )
        if ok:
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.NextBlock,
                QTextCursor.MoveMode.MoveAnchor,
                line - 1,
            )
            self._editor.setTextCursor(cursor)
            self._editor.centerCursor()
            self._editor.setFocus()

    # ── LLM controls ─────────────────────────────────────────────

    @Slot(bool, int)
    def _on_llm_slow_mode(self, slow: bool, latency_ms: int) -> None:
        if not self._config.get('autocomplete', 'enabled'):
            self._window._status_bar.show_slow_indicator(False)
            return
        if not self._config.get('autocomplete', 'llm_enabled'):
            self._window._status_bar.show_slow_indicator(False)
            return
        if slow:
            ms = latency_ms
            label = f"{ms / 1000:.1f}s" if ms >= 1000 else f"{ms}ms"
            self._window._status_bar.show_slow_indicator(True, f"Slow {label}")
        else:
            self._window._status_bar.show_slow_indicator(False)

    # ── Cursor / status ──────────────────────────────────────────

    @Slot()
    def _update_cursor(self) -> None:
        cursor = self._editor.textCursor()
        ln = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self._window._status_bar.update_cursor(ln, col)
        self._window._status_bar.update_line_count(self._editor.blockCount())
