"""Compatibility shim for autocomplete service."""

from services.autocomplete_service import (  # noqa: F401
    AutocompleteController,
    AutocompleteEngine,
    AutocompleteSettings,
)

__all__ = [
    "AutocompleteController",
    "AutocompleteEngine",
    "AutocompleteSettings",
]
