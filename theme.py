"""Theme management with Windows dark/light mode detection."""
import sys
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

if sys.platform == 'win32':
    import winreg


DARK_COLORS = {
    'editor_bg': '#1e1e1e',
    'editor_fg': '#d4d4d4',
    'gutter_bg': '#252526',
    'line_number': '#858585',
    'current_line': '#2d2d30',
    'selection': '#264f78',
    'keyword': '#569cd6',
    'comment': '#6a9955',
    'string': '#ce9178',
    'operator': '#d4d4d4',
    'function': '#dcdcaa',
    'class': '#4ec9b0',
    'builtin': '#c586c0',
    'variable': '#9cdcfe',
    'text': '#d4d4d4',
    'ghost_text': '#6f6f6f',
}

LIGHT_COLORS = {
    'editor_bg': '#ffffff',
    'editor_fg': '#000000',
    'gutter_bg': '#f3f3f3',
    'line_number': '#237893',
    'current_line': '#fffbdd',
    'selection': '#add6ff',
    'keyword': '#0000ff',
    'comment': '#008000',
    'string': '#a31515',
    'operator': '#000000',
    'function': '#795e26',
    'class': '#267f99',
    'builtin': '#af00db',
    'variable': '#001080',
    'text': '#000000',
    'ghost_text': '#a0a0a0',
}


class ThemeManager(QObject):
    """Manages theme detection and color schemes."""

    theme_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._theme = self._detect_system_theme()

    def _detect_system_theme(self) -> str:
        """Detect Windows dark/light mode from registry."""
        if sys.platform != 'win32':
            return 'light'
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows'
                r'\CurrentVersion\Themes\Personalize'
            )
            value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            winreg.CloseKey(key)
            return 'light' if value == 1 else 'dark'
        except (FileNotFoundError, OSError):
            return 'light'

    def get_theme(self) -> str:
        """Return current theme name."""
        return self._theme

    def get_colors(self) -> dict:
        """Return color dictionary for current theme."""
        return DARK_COLORS if self._theme == 'dark' else LIGHT_COLORS

    def get_color(self, key: str) -> QColor:
        """Return QColor for a color key."""
        return QColor(self.get_colors().get(key, '#000000'))

    def set_theme(self, theme: str) -> None:
        """Manually set theme."""
        if theme in ('dark', 'light') and theme != self._theme:
            self._theme = theme
            self.theme_changed.emit(theme)

    def refresh(self) -> None:
        """Re-detect system theme and emit if changed."""
        new_theme = self._detect_system_theme()
        if new_theme != self._theme:
            self._theme = new_theme
            self.theme_changed.emit(new_theme)
