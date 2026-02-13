"""Theme management with Windows dark/light mode detection.

Provides a ThemeManager that:
- Auto-detects Windows app theme via the registry
- Holds dark and light color palettes (VS Code-inspired)
- Emits a signal when the active theme changes
"""
import sys
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

# Windows registry access (only imported on win32)
if sys.platform == 'win32':
    import winreg


# ── Color palettes ───────────────────────────────────────────────
# Each dict maps semantic names to hex color strings.
# Keys are referenced by the editor, gutter, and syntax highlighter.

DARK_COLORS = {
    'editor_bg': '#1e1e1e',       # Editor background
    'editor_fg': '#d4d4d4',       # Default text color
    'gutter_bg': '#252526',       # Line-number gutter background
    'line_number': '#858585',     # Line-number text color
    'current_line': '#2d2d30',    # Current-line highlight
    'selection': '#264f78',       # Selection background
    'keyword': '#569cd6',         # Keywords (if, def, class, ...)
    'comment': '#6a9955',         # Comments
    'string': '#ce9178',          # String literals
    'operator': '#d4d4d4',        # Operators (+, -, =, ...)
    'function': '#dcdcaa',        # Function names
    'class': '#4ec9b0',           # Class names
    'builtin': '#c586c0',         # Built-in names (print, len, ...)
    'variable': '#9cdcfe',        # Variable names
    'text': '#d4d4d4',            # Generic text
    'ghost_text': '#6f6f6f',      # Autocomplete ghost overlay
    'bracket_match': '#c8c800',   # Matching bracket highlight
    'find_match': '#c8c800',      # Find highlight
    'accent': '#4fc1ff',          # UI accent (labels, emphasis)
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
    'bracket_match': '#ffff00',   # Matching bracket highlight
    'find_match': '#fff2a8',      # Find highlight
    'accent': '#0066bf',          # UI accent (labels, emphasis)
}


class ThemeManager(QObject):
    """Manages the active color theme and notifies listeners on change.

    Signals:
        theme_changed(str): Emitted with 'dark' or 'light' when the
            active theme is switched.
    """

    theme_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        # Detect the OS preference at startup
        self._theme = self._detect_system_theme()

    def _detect_system_theme(self) -> str:
        """Read the Windows 'AppsUseLightTheme' registry value.

        Returns 'dark' when the value is 0, 'light' otherwise.
        Falls back to 'light' on non-Windows platforms or errors.
        """
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
        """Return the current theme name ('dark' or 'light')."""
        return self._theme

    def get_colors(self) -> dict:
        """Return the full color dictionary for the active theme."""
        return DARK_COLORS if self._theme == 'dark' else LIGHT_COLORS

    def get_color(self, key: str) -> QColor:
        """Return a QColor for a single semantic color *key*."""
        return QColor(self.get_colors().get(key, '#000000'))

    def set_theme(self, theme: str) -> None:
        """Manually switch to *theme* ('dark' or 'light').

        Emits theme_changed only when the value actually changes.
        """
        if theme in ('dark', 'light') and theme != self._theme:
            self._theme = theme
            self.theme_changed.emit(theme)

    def refresh(self) -> None:
        """Re-detect system theme and emit if it changed."""
        new_theme = self._detect_system_theme()
        if new_theme != self._theme:
            self._theme = new_theme
            self.theme_changed.emit(new_theme)
