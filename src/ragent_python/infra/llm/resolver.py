"""Generation adapter resolver.

The resolver walks `settings.llm_fallback_chain` and returns the first
adapter that reports `is_available() == True`. Today only the mock provider
is implemented; real providers (OpenAI / Anthropic / Ollama) are registered
here in a follow-up step and gated by either an API key being present or a
reachable local endpoint.

`/healthz` exposes the resolved provider name so E2E checks can refuse a
``"mock"`` provider when running against staging or production profiles.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Callable

from ragent_python.config import get_settings
from ragent_python.core.generation.adapter import GenerationAdapter
from ragent_python.infra.llm.mock import MockGenerationAdapter


ProviderBuilder = Callable[[], GenerationAdapter]


def _build_mock() -> GenerationAdapter:
    return MockGenerationAdapter()


_PROVIDER_BUILDERS: dict[str, ProviderBuilder] = {
    "mock": _build_mock,
}


def list_known_providers() -> list[str]:
    return list(_PROVIDER_BUILDERS.keys())


def _parse_chain(raw: str) -> list[str]:
    return [name.strip().lower() for name in raw.split(",") if name.strip()]


@lru_cache(maxsize=1)
def resolve_generation_adapter() -> GenerationAdapter:
    settings = get_settings()
    explicit = settings.llm_provider.strip().lower()
    if explicit and explicit != "auto":
        builder = _PROVIDER_BUILDERS.get(explicit)
        if builder is not None:
            adapter = builder()
            if adapter.is_available():
                return adapter

    chain = _parse_chain(settings.llm_fallback_chain)
    for name in chain:
        builder = _PROVIDER_BUILDERS.get(name)
        if builder is None:
            continue
        adapter = builder()
        if adapter.is_available():
            return adapter

    return MockGenerationAdapter()


def clear_resolver_cache() -> None:
    resolve_generation_adapter.cache_clear()
