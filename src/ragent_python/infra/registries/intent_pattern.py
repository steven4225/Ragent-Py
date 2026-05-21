"""Intent pattern registry.

Modules declare their activation vocabulary via `IntentPattern`; the registry
holds them so the (future) router can iterate all known patterns and select a
match. Step A only ships the container — the keyword-based matching lives on
`IntentPattern.matches()` itself.
"""

from __future__ import annotations

from ragent_python.core.router.intent import IntentPattern


class IntentPatternRegistry:
    def __init__(self) -> None:
        self._patterns: dict[str, IntentPattern] = {}

    def register(self, pattern: IntentPattern) -> None:
        if pattern.name in self._patterns:
            raise ValueError(f"Intent pattern '{pattern.name}' already registered.")
        self._patterns[pattern.name] = pattern

    def get(self, name: str) -> IntentPattern | None:
        return self._patterns.get(name)

    def list_patterns(self) -> list[IntentPattern]:
        return list(self._patterns.values())

    def match(self, query: str) -> list[IntentPattern]:
        return [pattern for pattern in self._patterns.values() if pattern.matches(query)]

    def clear(self) -> None:
        self._patterns.clear()


default_intent_pattern_registry = IntentPatternRegistry()
