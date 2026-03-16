"""Status bar widget — shows cursor position, font size, encoding, LLM state."""
from __future__ import annotations

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QStatusBar, QLabel, QToolButton


class StatusBarView(QStatusBar):
    """Self-contained status bar that owns its child widgets.

    Signals:
        llm_toggled(bool): Emitted when the user clicks the LLM toggle button.

    Slots:
        update_cursor(ln, col)
        update_font_size(size)
        update_line_count(count)
        update_llm_state(enabled, available)
        show_slow_indicator(visible, text)
    """

    llm_toggled = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_widgets()

    def _build_widgets(self) -> None:
        self._pos_label = QLabel('Ln 1, Col 1')
        self._font_label = QLabel('Font 12pt')
        self._enc_label = QLabel('UTF-8')
        self._lines_label = QLabel('1 lines')

        self._llm_toggle = QToolButton()
        self._llm_toggle.setObjectName('llmToggle')
        self._llm_toggle.setCheckable(True)
        self._llm_toggle.setText('LLM: N/A')
        self._llm_toggle.setToolTip('Toggle LLM suggestions')
        self._llm_toggle.clicked.connect(lambda checked: self.llm_toggled.emit(checked))

        self._llm_slow = QLabel('Slow')
        self._llm_slow.setObjectName('llmSlow')
        self._llm_slow.hide()

        self.addPermanentWidget(self._pos_label)
        self.addPermanentWidget(self._font_label)
        self.addPermanentWidget(self._enc_label)
        self.addPermanentWidget(self._lines_label)
        self.addPermanentWidget(self._llm_toggle)
        self.addPermanentWidget(self._llm_slow)

    # ── Public slots ─────────────────────────────────────────────

    @Slot(int, int)
    def update_cursor(self, ln: int, col: int) -> None:
        self._pos_label.setText(f'Ln {ln}, Col {col}')

    @Slot(int)
    def update_font_size(self, size: int) -> None:
        self._font_label.setText(f'Font {size}pt')

    @Slot(int)
    def update_line_count(self, count: int) -> None:
        self._lines_label.setText(f'{count} lines')

    @Slot(bool, bool)
    def update_llm_state(self, enabled: bool, available: bool) -> None:
        """Sync the LLM toggle button state.

        Args:
            enabled:   Whether LLM suggestions are currently on.
            available: Whether the autocomplete service is loaded.
        """
        self._llm_toggle.setEnabled(available)
        self._llm_toggle.setChecked(enabled and available)
        if not available:
            self._llm_toggle.setText('LLM: N/A')
        else:
            self._llm_toggle.setText('LLM: On' if enabled else 'LLM: Off')
        if not enabled or not available:
            self._llm_slow.hide()

    @Slot(bool, str)
    def show_slow_indicator(self, visible: bool, text: str = '') -> None:
        if visible:
            self._llm_slow.setText(text)
            self._llm_slow.show()
        else:
            self._llm_slow.hide()
