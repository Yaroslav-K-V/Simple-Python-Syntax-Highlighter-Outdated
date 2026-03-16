"""Find & Replace toolbar widget — pure View.

Emits user actions as signals; all search/replace logic lives in
FindController.  This widget only handles UI layout, theme styling,
and passing user input to the controller via signals.
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QToolButton, QCheckBox,
    QLabel, QStyle, QPushButton,
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QKeySequence, QShortcut

from controllers.find_controller import FindController


class FindBar(QWidget):
    """Find & Replace toolbar.

    Signals:
        closed: Emitted when the bar is dismissed (Escape or close button).
    """

    closed = Signal()

    def __init__(self, editor, theme_manager, parent=None) -> None:
        super().__init__(parent)
        self._editor = editor
        self._theme = theme_manager
        self._theme.theme_changed.connect(self._apply_theme)
        self._replace_visible = False
        self.setObjectName('findBar')

        # Controller that owns all search/replace/highlight logic
        self._ctrl = FindController(editor, theme_manager)
        self._ctrl.match_count_updated.connect(self._on_match_count)

        self._setup_ui()
        self._apply_theme(self._theme.get_theme())
        self.hide()

    # ── UI construction ──────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(4, 4, 4, 4)
        outer_layout.setSpacing(4)

        # ── Find row ──
        find_layout = QHBoxLayout()
        find_layout.setSpacing(6)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText('Find...')
        self._search_input.textChanged.connect(self._on_query_changed)
        self._search_input.returnPressed.connect(self.find_next)
        find_layout.addWidget(self._search_input)

        self._count_label = QLabel('')
        self._count_label.setObjectName('matchCount')
        self._count_label.setAlignment(Qt.AlignCenter)
        self._count_label.setMinimumWidth(52)
        find_layout.addWidget(self._count_label)

        self._case_check = QCheckBox('Aa')
        self._case_check.setToolTip('Match case')
        self._case_check.toggled.connect(self._on_query_changed)
        find_layout.addWidget(self._case_check)

        prev_btn = self._make_tool_button(
            QStyle.SP_ArrowBack, 'Previous (Shift+F3)', self.find_prev
        )
        find_layout.addWidget(prev_btn)

        next_btn = self._make_tool_button(
            QStyle.SP_ArrowForward, 'Next (F3)', self.find_next
        )
        find_layout.addWidget(next_btn)

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

        QShortcut(QKeySequence('Escape'), self, self._close)

    def _make_tool_button(self, icon_style, tooltip, handler) -> QToolButton:
        btn = QToolButton()
        btn.setIcon(self.style().standardIcon(icon_style))
        btn.setIconSize(QSize(14, 14))
        btn.setToolTip(tooltip)
        btn.setAutoRaise(True)
        btn.setFixedSize(26, 24)
        btn.clicked.connect(handler)
        return btn

    def _apply_theme(self, _: str) -> None:
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
            self._ctrl.highlight_all(
                self._search_input.text(), self._case_check.isChecked()
            )

    # ── Show / hide ──────────────────────────────────────────────

    def show_and_focus(self, show_replace: bool = False) -> None:
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
            self._ctrl.highlight_all(
                self._search_input.text(), self._case_check.isChecked()
            )

    def _close(self) -> None:
        self.hide()
        self._replace_row.hide()
        self._replace_visible = False
        self._ctrl.clear_highlights()
        self._editor.setFocus()
        self.closed.emit()

    # ── Slots from search input ───────────────────────────────────

    def _on_query_changed(self) -> None:
        self._ctrl.highlight_all(
            self._search_input.text(), self._case_check.isChecked()
        )

    def _on_match_count(self, text: str) -> None:
        self._count_label.setText(text)

    # ── Navigation / Replace (public API for shortcuts) ──────────

    def find_next(self) -> None:
        self._ctrl.find_next(self._search_input.text(), self._case_check.isChecked())

    def find_prev(self) -> None:
        self._ctrl.find_prev(self._search_input.text(), self._case_check.isChecked())

    def replace_current(self) -> None:
        self._ctrl.replace_current(
            self._search_input.text(),
            self._replace_input.text(),
            self._case_check.isChecked(),
        )

    def replace_all(self) -> None:
        self._ctrl.replace_all(
            self._search_input.text(),
            self._replace_input.text(),
            self._case_check.isChecked(),
        )
