"""Intent pattern declaration.

A module declares the surface vocabulary that should activate its tools and
retrieval sources. Step A only ships the keyword-matching shape; an embedding
or LLM-based router can be plugged in later behind the same `IntentPattern`
description, since `matches()` is intentionally opaque.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class IntentPattern:
    name: str
    module: str
    keywords: tuple[str, ...] = ()
    suggested_tools: tuple[str, ...] = ()
    suggested_sources: tuple[str, ...] = ()
    description: str = ""
    weight: float = 1.0
    tags: tuple[str, ...] = field(default_factory=tuple)

    def matches(self, query: str) -> bool:
        if not self.keywords:
            return False
        lowered = query.lower()
        return any(keyword.lower() in lowered for keyword in self.keywords)
