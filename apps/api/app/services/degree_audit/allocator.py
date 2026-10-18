from __future__ import annotations

from uuid import UUID

SourceKey = tuple[str, UUID]


class AuditAllocator:
    def __init__(self) -> None:
        self._used_sources: set[SourceKey] = set()

    def is_available(self, source_key: SourceKey, *, allows_overlap: bool) -> bool:
        return allows_overlap or source_key not in self._used_sources

    def reserve(self, source_key: SourceKey, *, allows_overlap: bool) -> bool:
        is_shared = source_key in self._used_sources
        if not allows_overlap:
            self._used_sources.add(source_key)
        return is_shared
