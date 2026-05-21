"""LLM provider adapters and resolver.

Step A only ships the mock provider plus the resolver entrypoint. Real
provider implementations (`openai_provider.py`, `anthropic_provider.py`,
`ollama_provider.py`) land in a dedicated step before the e-commerce module
needs real generation.
"""

from ragent_python.infra.llm.mock import MockGenerationAdapter
from ragent_python.infra.llm.resolver import (
    list_known_providers,
    resolve_generation_adapter,
)

__all__ = [
    "MockGenerationAdapter",
    "list_known_providers",
    "resolve_generation_adapter",
]
