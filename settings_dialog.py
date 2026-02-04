"""Settings dialog for the editor."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSpinBox, QComboBox, QCheckBox, QPushButton,
    QFontComboBox, QGroupBox, QFormLayout, QLineEdit, QFileDialog,
    QDoubleSpinBox,
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
        tabs.addTab(self._create_autocomplete_tab(), 'Autocomplete')
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

    def _create_autocomplete_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        ac_group = QGroupBox('Autocomplete')
        ac_layout = QFormLayout(ac_group)

        self._ac_enabled = QCheckBox('Enable autocomplete')
        self._ac_enabled.setChecked(self._config.autocomplete_enabled)
        ac_layout.addRow(self._ac_enabled)

        model_row = QHBoxLayout()
        self._ac_model_dir = QLineEdit(self._config.autocomplete_model_dir)
        browse_btn = QPushButton('Browse...')
        browse_btn.clicked.connect(self._browse_model_dir)
        model_row.addWidget(self._ac_model_dir)
        model_row.addWidget(browse_btn)
        ac_layout.addRow('Model folder:', model_row)

        self._ac_device = QComboBox()
        self._ac_device.addItem('Auto', 'auto')
        self._ac_device.addItem('CPU', 'cpu')
        self._ac_device.addItem('CUDA', 'cuda')
        device_idx = self._ac_device.findData(self._config.autocomplete_device)
        if device_idx >= 0:
            self._ac_device.setCurrentIndex(device_idx)
        ac_layout.addRow('Device:', self._ac_device)

        self._ac_max_tokens = QSpinBox()
        self._ac_max_tokens.setRange(1, 128)
        self._ac_max_tokens.setValue(self._config.autocomplete_max_new_tokens)
        ac_layout.addRow('Max new tokens:', self._ac_max_tokens)

        self._ac_context_tokens = QSpinBox()
        self._ac_context_tokens.setRange(128, 8192)
        self._ac_context_tokens.setValue(
            self._config.autocomplete_context_tokens
        )
        ac_layout.addRow('Context tokens:', self._ac_context_tokens)

        self._ac_context_chars = QSpinBox()
        self._ac_context_chars.setRange(0, 20000)
        self._ac_context_chars.setValue(
            self._config.autocomplete_context_chars
        )
        ac_layout.addRow('Context chars:', self._ac_context_chars)

        self._ac_temperature = QDoubleSpinBox()
        self._ac_temperature.setRange(0.0, 2.0)
        self._ac_temperature.setSingleStep(0.05)
        self._ac_temperature.setValue(self._config.autocomplete_temperature)
        ac_layout.addRow('Temperature:', self._ac_temperature)

        self._ac_top_p = QDoubleSpinBox()
        self._ac_top_p.setRange(0.1, 1.0)
        self._ac_top_p.setSingleStep(0.05)
        self._ac_top_p.setValue(self._config.autocomplete_top_p)
        ac_layout.addRow('Top-p:', self._ac_top_p)

        self._ac_debounce = QSpinBox()
        self._ac_debounce.setRange(0, 1000)
        self._ac_debounce.setValue(self._config.autocomplete_debounce_ms)
        ac_layout.addRow('Debounce (ms):', self._ac_debounce)

        self._ac_allow_strings = QCheckBox('Allow suggestions in strings/comments')
        self._ac_allow_strings.setChecked(
            self._config.autocomplete_allow_in_strings
        )
        ac_layout.addRow(self._ac_allow_strings)

        layout.addWidget(ac_group)
        layout.addStretch()

        return widget

    def _browse_model_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, 'Select Model Folder', self._ac_model_dir.text()
        )
        if path:
            self._ac_model_dir.setText(path)

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
        self._config.set('autocomplete', 'enabled',
                         self._ac_enabled.isChecked())
        self._config.set('autocomplete', 'model_dir',
                         self._ac_model_dir.text())
        self._config.set('autocomplete', 'device',
                         self._ac_device.currentData())
        self._config.set('autocomplete', 'max_new_tokens',
                         self._ac_max_tokens.value())
        self._config.set('autocomplete', 'context_tokens',
                         self._ac_context_tokens.value())
        self._config.set('autocomplete', 'context_chars',
                         self._ac_context_chars.value())
        self._config.set('autocomplete', 'temperature',
                         self._ac_temperature.value())
        self._config.set('autocomplete', 'top_p',
                         self._ac_top_p.value())
        self._config.set('autocomplete', 'debounce_ms',
                         self._ac_debounce.value())
        self._config.set('autocomplete', 'allow_in_strings',
                         self._ac_allow_strings.isChecked())
        self._config.save()
        self.settings_changed.emit()

    def _save_and_close(self) -> None:
        """Save settings and close dialog."""
        self._apply_settings()
        self.accept()
