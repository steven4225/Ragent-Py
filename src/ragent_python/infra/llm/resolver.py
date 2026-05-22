"""Generation adapter resolver.

The resolver walks `settings.llm_fallback_chain` and returns the first
adapter that reports `is_available() == True`. The chain is a comma-
separated list of provider names; today the registered builders are:

  * ``openai`` / ``openai_compatible``: any OpenAI-compatible service
    selected by ``OPENAI_BASE_URL`` and ``PYTHON_LLM_MODEL`` (works for
    OpenAI proper, Alibaba Cloud DashScope, Moonshot, DeepSeek,
    self-hosted vLLM, etc.; the platform does not bind to a vendor)
  * ``mock``: unconditional terminal fallback used in tests and dev

Anthropic / Ollama remain reserved provider names; their builders will
land in a follow-up push without changing the resolver contract.

``/healthz`` exposes the resolved provider name so E2E checks can refuse
a ``"mock"`` provider when running against staging or production.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Callable

from ragent_python.config import get_settings
from ragent_python.core.generation.adapter import GenerationAdapter
from ragent_python.infra.llm.mock import MockGenerationAdapter
from ragent_python.infra.llm.openai_compatible import OpenAICompatibleGenerationAdapter


ProviderBuilder = Callable[[], GenerationAdapter]


def _build_mock() -> GenerationAdapter:
    return MockGenerationAdapter()


def _build_openai_compatible() -> GenerationAdapter:
    return OpenAICompatibleGenerationAdapter()


_PROVIDER_BUILDERS: dict[str, ProviderBuilder] = {
    "mock": _build_mock,
    "openai": _build_openai_compatible,
    "openai_compatible": _build_openai_compatible,
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
