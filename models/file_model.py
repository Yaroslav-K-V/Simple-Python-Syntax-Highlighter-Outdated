"""File state model — tracks the open file path, dirty flag, and I/O.

No Qt widget references here.  The caller (AppController) is responsible
for reading the editor content and passing it to save().
"""
from __future__ import annotations

import os

from PySide6.QtCore import QObject, Signal


class FileModel(QObject):
    """Model that owns the current file path, unsaved state, and I/O.

    Signals:
        file_opened(str):    Emitted after a file is successfully read.
                             Carries the file path.
        file_saved(str):     Emitted after a file is successfully written.
                             Carries the file path.
        file_cleared():      Emitted when the buffer is reset (New File).
        unsaved_changed(bool): Emitted when the dirty flag changes.
        error_occurred(str): Emitted on I/O error with a human-readable message.
        content_ready(str):  Emitted by load() to deliver the file text to the View.
    """

    file_opened = Signal(str)
    file_saved = Signal(str)
    file_cleared = Signal()
    unsaved_changed = Signal(bool)
    error_occurred = Signal(str)
    content_ready = Signal(str)

    def __init__(self, config) -> None:
        super().__init__()
        self._config = config
        self._path: str | None = None
        self._unsaved: bool = False

    # ── Properties ───────────────────────────────────────────────

    @property
    def path(self) -> str | None:
        """Absolute path of the currently open file, or None if untitled."""
        return self._path

    @property
    def unsaved(self) -> bool:
        """True when the buffer has been modified since last save."""
        return self._unsaved

    @property
    def display_name(self) -> str:
        """Basename of the current file, or 'Untitled'."""
        return os.path.basename(self._path) if self._path else 'Untitled'

    # ── State mutators ───────────────────────────────────────────

    def mark_modified(self) -> None:
        """Mark the buffer as modified (called by CodeEditor.textChanged)."""
        if not self._unsaved:
            self._unsaved = True
            self.unsaved_changed.emit(True)

    def mark_clean(self) -> None:
        """Mark the buffer as clean (called after successful save)."""
        if self._unsaved:
            self._unsaved = False
            self.unsaved_changed.emit(False)

    # ── File operations ──────────────────────────────────────────

    def load(self, path: str) -> None:
        """Read *path* from disk and emit content_ready with the text.

        On success emits file_opened(path).
        On failure emits error_occurred(message).
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            self._path = path
            self._unsaved = False
            self._config.set('files', 'last_opened', path)
            self._config.save()
            self.content_ready.emit(text)
            self.file_opened.emit(path)
        except FileNotFoundError:
            self.error_occurred.emit(f'File not found: {path}')
        except PermissionError:
            self.error_occurred.emit(f'Permission denied: {path}')
        except UnicodeDecodeError:
            self.error_occurred.emit(f'Cannot decode file (not UTF-8): {path}')
        except OSError as e:
            self.error_occurred.emit(f'Failed to read: {e}')

    def save(self, content: str, path: str | None = None, trim_whitespace: bool = False) -> bool:
        """Write *content* to *path* (or the current path).

        Args:
            content:        Text to write.
            path:           Target path.  Uses self._path when None.
            trim_whitespace: Strip trailing whitespace from each line.

        Returns True on success, False on failure.
        On success emits file_saved(path).
        On failure emits error_occurred(message).
        """
        target = path or self._path
        if not target:
            return False
        try:
            if trim_whitespace:
                lines = [line.rstrip() for line in content.split('\n')]
                content = '\n'.join(lines)
            with open(target, 'w', encoding='utf-8') as f:
                f.write(content)
            self._path = target
            self._unsaved = False
            self._config.set('files', 'last_opened', target)
            self._config.save()
            self.file_saved.emit(target)
            return True
        except PermissionError:
            self.error_occurred.emit(f'Permission denied: {target}')
            return False
        except OSError as e:
            self.error_occurred.emit(f'Failed to save: {e}')
            return False

    def clear(self) -> None:
        """Reset to an untitled, clean buffer state."""
        self._path = None
        self._unsaved = False
        self.file_cleared.emit()
