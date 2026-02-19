"""Settings dialog for the editor.

A tabbed QDialog that lets the user configure:
- Editor: font, indentation, line numbers
- Appearance: color theme (auto / dark / light)
- Files: trailing whitespace trimming
- Autocomplete: model path, device, sampling parameters
"""
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
    """Modal dialog with tabs for different setting categories.

    Signals:
        settings_changed: Emitted after the user clicks OK or Apply,
            so the main window can refresh its state.
    """

    settings_changed = Signal()

    def __init__(self, config: Config, theme_manager, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._theme = theme_manager
        # Keep dialog themed when the user toggles dark/light
        self._theme.theme_changed.connect(self._apply_theme)
        self.setWindowTitle('Settings')
        self.setMinimumWidth(400)
        self._setup_ui()
        self._apply_theme(self._theme.get_theme())

    # ── UI construction ──────────────────────────────────────────

    def _setup_ui(self) -> None:
        """Build tabs and OK / Cancel / Apply buttons."""
        layout = QVBoxLayout(self)

        # Tab widget with one tab per settings category
        tabs = QTabWidget()
        tabs.addTab(self._create_editor_tab(), 'Editor')
        tabs.addTab(self._create_appearance_tab(), 'Appearance')
        tabs.addTab(self._create_files_tab(), 'Files')
        tabs.addTab(self._create_autocomplete_tab(), 'Autocomplete')
        layout.addWidget(tabs)

        # Bottom button row
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

    # ── Tab builders ─────────────────────────────────────────────

    def _create_editor_tab(self) -> QWidget:
        """Build the Editor tab: font, indentation, display options."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # -- Font group --
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

        # -- Indentation group --
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

        # -- Display group --
        display_group = QGroupBox('Display')
        display_layout = QFormLayout(display_group)

        self._show_line_numbers = QCheckBox('Show line numbers')
        self._show_line_numbers.setChecked(self._config.show_line_numbers)
        display_layout.addRow(self._show_line_numbers)

        layout.addWidget(display_group)
        layout.addStretch()

        return widget

    def _create_appearance_tab(self) -> QWidget:
        """Build the Appearance tab: theme selector."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        theme_group = QGroupBox('Theme')
        theme_layout = QFormLayout(theme_group)

        self._theme_combo = QComboBox()
        self._theme_combo.addItem('Auto (follow system)', 'auto')
        self._theme_combo.addItem('Dark', 'dark')
        self._theme_combo.addItem('Light', 'light')
        # Select the currently saved theme
        current = self._config.theme
        idx = self._theme_combo.findData(current)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        theme_layout.addRow('Color theme:', self._theme_combo)

        layout.addWidget(theme_group)
        layout.addStretch()

        return widget

    def _create_files_tab(self) -> QWidget:
        """Build the Files tab: save-related options."""
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
        """Build the Autocomplete tab: model, device, and sampling settings."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        ac_group = QGroupBox('Autocomplete')
        ac_layout = QFormLayout(ac_group)

        # Enable / disable toggle
        self._ac_enabled = QCheckBox('Enable autocomplete')
        self._ac_enabled.setChecked(self._config.autocomplete_enabled)
        ac_layout.addRow(self._ac_enabled)

        self._ac_llm_enabled = QCheckBox('Enable model suggestions (LLM)')
        self._ac_llm_enabled.setChecked(self._config.autocomplete_llm_enabled)
        ac_layout.addRow(self._ac_llm_enabled)

        # Model directory with browse button
        model_row = QHBoxLayout()
        self._ac_model_dir = QLineEdit(self._config.autocomplete_model_dir)
        browse_btn = QPushButton('Browse...')
        browse_btn.clicked.connect(self._browse_model_dir)
        model_row.addWidget(self._ac_model_dir)
        model_row.addWidget(browse_btn)
        ac_layout.addRow('Model folder:', model_row)

        # Device selector
        self._ac_device = QComboBox()
        self._ac_device.addItem('Auto', 'auto')
        self._ac_device.addItem('CPU', 'cpu')
        self._ac_device.addItem('CUDA', 'cuda')
        device_idx = self._ac_device.findData(self._config.autocomplete_device)
        if device_idx >= 0:
            self._ac_device.setCurrentIndex(device_idx)
        ac_layout.addRow('Device:', self._ac_device)

        # Generation parameters
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

        # Sampling parameters
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

        # Debounce delay
        self._ac_debounce = QSpinBox()
        self._ac_debounce.setRange(0, 1000)
        self._ac_debounce.setValue(self._config.autocomplete_debounce_ms)
        ac_layout.addRow('Debounce (ms):', self._ac_debounce)

        # Behavior toggles
        self._ac_allow_strings = QCheckBox('Allow suggestions in strings/comments')
        self._ac_allow_strings.setChecked(
            self._config.autocomplete_allow_in_strings
        )
        ac_layout.addRow(self._ac_allow_strings)

        self._ac_llm_first = QCheckBox('Prefer model suggestions first')
        self._ac_llm_first.setChecked(self._config.autocomplete_llm_first)
        ac_layout.addRow(self._ac_llm_first)

        layout.addWidget(ac_group)
        layout.addStretch()

        return widget

    def _browse_model_dir(self) -> None:
        """Open a folder picker for the autocomplete model directory."""
        path = QFileDialog.getExistingDirectory(
            self, 'Select Model Folder', self._ac_model_dir.text()
        )
        if path:
            self._ac_model_dir.setText(path)

    # ── Settings persistence ─────────────────────────────────────

    def _apply_theme(self, _: str) -> None:
        """Re-style the dialog to match the active theme."""
        colors = self._theme.get_colors()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors['editor_bg']};
                color: {colors['editor_fg']};
            }}
            QTabWidget::pane {{
                border: 1px solid {colors['line_number']};
            }}
            QTabBar::tab {{
                background-color: {colors['gutter_bg']};
                color: {colors['editor_fg']};
                padding: 4px 10px;
                border: 1px solid {colors['line_number']};
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {colors['current_line']};
            }}
            QGroupBox {{
                border: 1px solid {colors['line_number']};
                margin-top: 10px;
                color: {colors['editor_fg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
                background-color: {colors['editor_bg']};
            }}
            QLabel {{
                color: {colors['editor_fg']};
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {colors['editor_bg']};
                color: {colors['editor_fg']};
                border: 1px solid {colors['line_number']};
                padding: 2px 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {colors['editor_bg']};
                color: {colors['editor_fg']};
                selection-background-color: {colors['selection']};
            }}
            QPushButton {{
                background-color: {colors['gutter_bg']};
                color: {colors['editor_fg']};
                border: 1px solid {colors['line_number']};
                padding: 2px 10px;
            }}
            QPushButton:hover {{
                background-color: {colors['selection']};
            }}
            QCheckBox {{
                color: {colors['editor_fg']};
            }}
        """)

    def _apply_settings(self) -> None:
        """Read all UI widgets and write values to Config, then save."""
        # Editor settings
        self._config.set('editor', 'font_family',
                         self._font_combo.currentFont().family())
        self._config.set('editor', 'font_size', self._font_size.value())
        self._config.set('editor', 'tab_size', self._tab_size.value())
        self._config.set('editor', 'use_spaces', self._use_spaces.isChecked())
        self._config.set('editor', 'show_line_numbers',
                         self._show_line_numbers.isChecked())
        # Appearance
        self._config.set('appearance', 'theme',
                         self._theme_combo.currentData())
        # Files
        self._config.set('files', 'trim_whitespace',
                         self._trim_whitespace.isChecked())
        # Autocomplete
        self._config.set('autocomplete', 'enabled',
                         self._ac_enabled.isChecked())
        self._config.set('autocomplete', 'llm_enabled',
                         self._ac_llm_enabled.isChecked())
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
        self._config.set('autocomplete', 'llm_first',
                         self._ac_llm_first.isChecked())
        # Persist and notify
        self._config.save()
        self.settings_changed.emit()

    def _save_and_close(self) -> None:
        """Apply settings and close the dialog."""
        self._apply_settings()
        self.accept()
