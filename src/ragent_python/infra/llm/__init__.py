"""LLM provider adapters and resolver.

`OpenAICompatibleGenerationAdapter` is vendor-agnostic and covers OpenAI
proper, Alibaba Cloud DashScope (OpenAI-compatible mode), Moonshot,
DeepSeek, self-hosted vLLM / SGLang, etc. by switching `OPENAI_BASE_URL`
and `PYTHON_LLM_MODEL`. Anthropic / Ollama remain reserved provider
names for a follow-up push.
"""

from ragent_python.infra.llm.mock import MockGenerationAdapter
from ragent_python.infra.llm.openai_compatible import OpenAICompatibleGenerationAdapter
from ragent_python.infra.llm.resolver import (
    list_known_providers,
    resolve_generation_adapter,
)

__all__ = [
    "MockGenerationAdapter",
    "OpenAICompatibleGenerationAdapter",
    "list_known_providers",
    "resolve_generation_adapter",
]
