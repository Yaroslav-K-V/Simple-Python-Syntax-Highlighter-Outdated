"""Settings dialog for the editor."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSpinBox, QComboBox, QCheckBox, QPushButton,
    QFontComboBox, QGroupBox, QFormLayout,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Signal

from config import Config


class SettingsDialog(QDialog):
    """Settings dialog with tabs for different categories."""

    settings_changed = Signal()

    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle('Settings')
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_editor_tab(), 'Editor')
        tabs.addTab(self._create_appearance_tab(), 'Appearance')
        tabs.addTab(self._create_files_tab(), 'Files')
        layout.addWidget(tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton('OK')
        ok_btn.clicked.connect(self._save_and_close)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        apply_btn = QPushButton('Apply')
        apply_btn.clicked.connect(self._apply_settings)
        btn_layout.addWidget(apply_btn)

        layout.addLayout(btn_layout)

    def _create_editor_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Font group
        font_group = QGroupBox('Font')
        font_layout = QFormLayout(font_group)

        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont(self._config.font_family))
        font_layout.addRow('Family:', self._font_combo)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 72)
        self._font_size.setValue(self._config.font_size)
        font_layout.addRow('Size:', self._font_size)

        layout.addWidget(font_group)

        # Indentation group
        indent_group = QGroupBox('Indentation')
        indent_layout = QFormLayout(indent_group)

        self._tab_size = QSpinBox()
        self._tab_size.setRange(1, 8)
        self._tab_size.setValue(self._config.tab_size)
        indent_layout.addRow('Tab size:', self._tab_size)

        self._use_spaces = QCheckBox('Insert spaces instead of tabs')
        self._use_spaces.setChecked(self._config.use_spaces)
        indent_layout.addRow(self._use_spaces)

        layout.addWidget(indent_group)

        # Display group
        display_group = QGroupBox('Display')
        display_layout = QFormLayout(display_group)

        self._show_line_numbers = QCheckBox('Show line numbers')
        self._show_line_numbers.setChecked(self._config.show_line_numbers)
        display_layout.addRow(self._show_line_numbers)

        layout.addWidget(display_group)
        layout.addStretch()

        return widget

    def _create_appearance_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        theme_group = QGroupBox('Theme')
        theme_layout = QFormLayout(theme_group)

        self._theme_combo = QComboBox()
        self._theme_combo.addItem('Auto (follow system)', 'auto')
        self._theme_combo.addItem('Dark', 'dark')
        self._theme_combo.addItem('Light', 'light')
        current = self._config.theme
        idx = self._theme_combo.findData(current)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        theme_layout.addRow('Color theme:', self._theme_combo)

        layout.addWidget(theme_group)
        layout.addStretch()

        return widget

    def _create_files_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        save_group = QGroupBox('Saving')
        save_layout = QFormLayout(save_group)

        self._trim_whitespace = QCheckBox('Trim trailing whitespace on save')
        self._trim_whitespace.setChecked(self._config.trim_whitespace)
        save_layout.addRow(self._trim_whitespace)

        layout.addWidget(save_group)
        layout.addStretch()

        return widget

    def _load_settings(self) -> None:
        """Load current settings into UI."""
        pass  # Already done in _setup_ui

    def _apply_settings(self) -> None:
        """Apply settings without closing."""
        self._config.set('editor', 'font_family',
                         self._font_combo.currentFont().family())
        self._config.set('editor', 'font_size', self._font_size.value())
        self._config.set('editor', 'tab_size', self._tab_size.value())
        self._config.set('editor', 'use_spaces', self._use_spaces.isChecked())
        self._config.set('editor', 'show_line_numbers',
                         self._show_line_numbers.isChecked())
        self._config.set('appearance', 'theme',
                         self._theme_combo.currentData())
        self._config.set('files', 'trim_whitespace',
                         self._trim_whitespace.isChecked())
        self._config.save()
        self.settings_changed.emit()

    def _save_and_close(self) -> None:
        """Save settings and close dialog."""
        self._apply_settings()
        self.accept()
