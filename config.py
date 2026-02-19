"""Configuration management for the editor.

Persists user settings as JSON in ~/.pyglow/settings.json.
Missing keys are automatically filled from DEFAULT_CONFIG on load.
"""
import json
import os
from pathlib import Path
from typing import Any


# Default values for every configuration key.
# Sections: editor, appearance, files, autocomplete.
DEFAULT_CONFIG = {
    'editor': {
        'font_family': 'Consolas',       # Monospace font for the editor
        'font_size': 10,                 # Font size in pt
        'tab_size': 4,                   # Spaces per indent level
        'use_spaces': True,              # True = spaces, False = real tabs
        'show_line_numbers': True,       # Toggle line-number gutter
    },
    'appearance': {
        'theme': 'auto',  # 'auto' follows OS, or 'dark' / 'light'
    },
    'files': {
        'trim_whitespace': False,        # Strip trailing spaces on save
        'auto_save': False,              # (future) periodic auto-save
        'auto_save_interval': 30,        # Seconds between auto-saves
        'last_opened': '',               # Path to the last opened file
    },
    'autocomplete': {
        'enabled': True,                 # Enable autocomplete (symbol + LLM)
        'llm_enabled': True,             # Enable LLM suggestions
        'model_dir': 'model',            # Path to the model directory
        'device': 'auto',               # 'auto', 'cpu', or 'cuda'
        'max_new_tokens': 32,            # Max tokens per suggestion
        'context_tokens': 1024,          # Token window sent to the model
        'context_chars': 4000,           # Character limit for context
        'temperature': 0.0,              # Sampling temperature
        'top_p': 0.9,                    # Nucleus sampling threshold
        'debounce_ms': 150,              # Delay before requesting a suggestion
        'allow_in_strings': False,       # Suggest inside string literals
        'llm_first': True,              # Prefer LLM over keyword completion
        'slow_mode_ms': 900,             # Slow-mode indicator threshold
    },
}


class Config:
    """Manages reading, writing, and accessing application settings.

    Settings are stored in ``~/.pyglow/settings.json``.
    On first run the file does not exist and all defaults apply.
    """

    def __init__(self) -> None:
        self._config_dir = Path.home() / '.pyglow'
        self._config_file = self._config_dir / 'settings.json'
        self._data: dict = {}
        self._load()

    # ── Persistence ──────────────────────────────────────────────

    def _load(self) -> None:
        """Load config from disk; fall back to empty dict on error."""
        if self._config_file.exists():
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}
        # Fill any missing keys with defaults
        self._merge_defaults()

    def _merge_defaults(self) -> None:
        """Ensure every key from DEFAULT_CONFIG exists in _data."""
        for section, values in DEFAULT_CONFIG.items():
            if section not in self._data:
                self._data[section] = {}
            for key, default in values.items():
                if key not in self._data[section]:
                    self._data[section][key] = default

    def save(self) -> None:
        """Write current settings to disk (creates dir if needed)."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with open(self._config_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2)

    # ── Generic accessors ────────────────────────────────────────

    def get(self, section: str, key: str) -> Any:
        """Get a config value, falling back to the default if absent."""
        return self._data.get(section, {}).get(
            key, DEFAULT_CONFIG.get(section, {}).get(key)
        )

    def set(self, section: str, key: str, value: Any) -> None:
        """Set a config value (does NOT auto-save)."""
        if section not in self._data:
            self._data[section] = {}
        self._data[section][key] = value

    # ── Convenience properties ───────────────────────────────────
    # These provide typed, attribute-style access to common settings.

    @property
    def font_family(self) -> str:
        """Editor font family name."""
        return self.get('editor', 'font_family')

    @property
    def font_size(self) -> int:
        """Editor font size in points."""
        return self.get('editor', 'font_size')

    @property
    def tab_size(self) -> int:
        """Number of spaces per tab stop."""
        return self.get('editor', 'tab_size')

    @property
    def use_spaces(self) -> bool:
        """Whether to insert spaces instead of tab characters."""
        return self.get('editor', 'use_spaces')

    @property
    def show_line_numbers(self) -> bool:
        """Whether to display the line-number gutter."""
        return self.get('editor', 'show_line_numbers')

    @property
    def theme(self) -> str:
        """Active theme: 'auto', 'dark', or 'light'."""
        return self.get('appearance', 'theme')

    @property
    def trim_whitespace(self) -> bool:
        """Whether to strip trailing whitespace on save."""
        return self.get('files', 'trim_whitespace')

    @property
    def last_opened(self) -> str:
        """Path to the last opened file (empty string if none)."""
        return self.get('files', 'last_opened')

    @property
    def autocomplete_enabled(self) -> bool:
        """Whether autocomplete is turned on."""
        return self.get('autocomplete', 'enabled')

    @property
    def autocomplete_llm_enabled(self) -> bool:
        """Whether LLM suggestions are turned on."""
        return self.get('autocomplete', 'llm_enabled')

    @property
    def autocomplete_model_dir(self) -> str:
        """Path to the autocomplete model directory."""
        return self.get('autocomplete', 'model_dir')

    @property
    def autocomplete_device(self) -> str:
        """Compute device: 'auto', 'cpu', or 'cuda'."""
        return self.get('autocomplete', 'device')

    @property
    def autocomplete_max_new_tokens(self) -> int:
        """Maximum tokens generated per suggestion."""
        return self.get('autocomplete', 'max_new_tokens')

    @property
    def autocomplete_context_tokens(self) -> int:
        """Token window size sent to the model."""
        return self.get('autocomplete', 'context_tokens')

    @property
    def autocomplete_context_chars(self) -> int:
        """Character limit for context sent to the model."""
        return self.get('autocomplete', 'context_chars')

    @property
    def autocomplete_temperature(self) -> float:
        """Sampling temperature (0.0 = deterministic)."""
        return self.get('autocomplete', 'temperature')

    @property
    def autocomplete_top_p(self) -> float:
        """Nucleus sampling probability threshold."""
        return self.get('autocomplete', 'top_p')

    @property
    def autocomplete_debounce_ms(self) -> int:
        """Milliseconds to wait before requesting a suggestion."""
        return self.get('autocomplete', 'debounce_ms')

    @property
    def autocomplete_allow_in_strings(self) -> bool:
        """Whether to suggest inside string literals and comments."""
        return self.get('autocomplete', 'allow_in_strings')

    @property
    def autocomplete_llm_first(self) -> bool:
        """Whether to prefer model suggestions over keyword matches."""
        return self.get('autocomplete', 'llm_first')

    @property
    def autocomplete_slow_mode_ms(self) -> int:
        """Threshold in ms to mark model suggestions as slow."""
        return self.get('autocomplete', 'slow_mode_ms')
