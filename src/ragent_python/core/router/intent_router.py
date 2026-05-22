"""Keyword-driven intent router on top of `IntentPatternRegistry`.

The router is intentionally simple — no LLM, no embeddings, no semantic
similarity. Each module declares its activation vocabulary via
`IntentPattern.keywords`; at request time we ask the registry which
patterns match and pick the highest-weighted hit. False positives are
acceptable here because the main chat UI gates this whole code path
behind an explicit "Ecommerce mode" toggle (see `ChatShell`): if the
toggle is off, this router is not consulted at all.

The router is *not* an interceptor on the main chat stream. It is a
classifier that the new `/internal/chat/router/stream` endpoint
consults to decide whether a request should be dispatched to the
ecommerce preview lane or delegated unchanged to the existing
`chat_service` stream generator. Both branches end up emitting the
same wire protocol — see `modules/ecommerce/chat_stream_bridge.py` for
the ecommerce-to-main translation.
"""

from __future__ import annotations

from dataclasses import dataclass

from ragent_python.core.router.intent import IntentPattern
from ragent_python.infra.registries.intent_pattern import (
    IntentPatternRegistry,
    default_intent_pattern_registry,
)


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """The outcome of `IntentRouter.classify()`.

    `intent` is the name of the winning `IntentPattern` (or `None` if
    no pattern matched). `module` is the module that owns the pattern,
    so the dispatcher does not need a second lookup. `matched` is the
    full list of matched patterns sorted by descending weight, kept
    for tracing/debugging.
    """

    intent: str | None
    module: str | None
    matched: tuple[IntentPattern, ...]

    @property
    def is_match(self) -> bool:
        return self.intent is not None


class IntentRouter:
    def __init__(
        self,
        *,
        registry: IntentPatternRegistry | None = None,
    ) -> None:
        self._registry = registry or default_intent_pattern_registry

    def classify(self, query: str) -> RoutingDecision:
        candidates = self._registry.match(query)
        if not candidates:
            return RoutingDecision(intent=None, module=None, matched=())
        ordered = tuple(sorted(candidates, key=lambda p: p.weight, reverse=True))
        winner = ordered[0]
        return RoutingDecision(
            intent=winner.name,
            module=winner.module,
            matched=ordered,
        )

    def classify_for_module(self, query: str, *, module: str) -> RoutingDecision:
        """Same as `classify()` but only considers patterns owned by
        `module`. Used by the toggled-router path where the UI has
        already declared the user wants ecommerce; we still run the
        classifier to suppress obvious false positives like
        ``my computer crashed``.
        """

        candidates = [
            pattern
            for pattern in self._registry.match(query)
            if pattern.module == module
        ]
        if not candidates:
            return RoutingDecision(intent=None, module=None, matched=())
        ordered = tuple(sorted(candidates, key=lambda p: p.weight, reverse=True))
        winner = ordered[0]
        return RoutingDecision(
            intent=winner.name,
            module=winner.module,
            matched=ordered,
        )


default_intent_router = IntentRouter()
