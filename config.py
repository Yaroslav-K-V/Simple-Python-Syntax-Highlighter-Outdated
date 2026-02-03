"""Configuration management for the editor."""
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    'editor': {
        'font_family': 'Consolas',
        'font_size': 10,
        'tab_size': 4,
        'use_spaces': True,
        'show_line_numbers': True,
    },
    'appearance': {
        'theme': 'auto',  # 'auto', 'dark', 'light'
    },
    'files': {
        'trim_whitespace': False,
        'auto_save': False,
        'auto_save_interval': 30,
    },
}


class Config:
    """Manages application configuration."""

    def __init__(self) -> None:
        self._config_dir = Path.home() / '.python-highlighter'
        self._config_file = self._config_dir / 'settings.json'
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        """Load config from file or use defaults."""
        if self._config_file.exists():
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}
        self._merge_defaults()

    def _merge_defaults(self) -> None:
        """Merge missing keys from defaults."""
        for section, values in DEFAULT_CONFIG.items():
            if section not in self._data:
                self._data[section] = {}
            for key, default in values.items():
                if key not in self._data[section]:
                    self._data[section][key] = default

    def save(self) -> None:
        """Save config to file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with open(self._config_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2)

    def get(self, section: str, key: str) -> Any:
        """Get a config value."""
        return self._data.get(section, {}).get(
            key, DEFAULT_CONFIG.get(section, {}).get(key)
        )

    def set(self, section: str, key: str, value: Any) -> None:
        """Set a config value."""
        if section not in self._data:
            self._data[section] = {}
        self._data[section][key] = value

    @property
    def font_family(self) -> str:
        return self.get('editor', 'font_family')

    @property
    def font_size(self) -> int:
        return self.get('editor', 'font_size')

    @property
    def tab_size(self) -> int:
        return self.get('editor', 'tab_size')

    @property
    def use_spaces(self) -> bool:
        return self.get('editor', 'use_spaces')

    @property
    def show_line_numbers(self) -> bool:
        return self.get('editor', 'show_line_numbers')

    @property
    def theme(self) -> str:
        return self.get('appearance', 'theme')

    @property
    def trim_whitespace(self) -> bool:
        return self.get('files', 'trim_whitespace')
