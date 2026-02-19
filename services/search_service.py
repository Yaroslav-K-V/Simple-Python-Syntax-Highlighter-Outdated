"""Pure text search helpers for the find bar."""

from __future__ import annotations


class SearchService:
    @staticmethod
    def find_positions(text: str, query: str, case_sensitive: bool) -> list[int]:
        if not query:
            return []
        if case_sensitive:
            haystack = text
            needle = query
        else:
            haystack = text.lower()
            needle = query.lower()
        positions = []
        start = 0
        step = max(1, len(needle))
        while True:
            idx = haystack.find(needle, start)
            if idx < 0:
                break
            positions.append(idx)
            start = idx + step
        return positions

    @staticmethod
    def match_index(positions: list[int], cursor_pos: int) -> int | None:
        if not positions:
            return None
        for i, pos in enumerate(positions):
            if pos >= cursor_pos:
                return i
        return 0
