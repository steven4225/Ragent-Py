"""Generation adapter contract.

Domain modules MUST NOT import any provider SDK (openai / anthropic / ollama /
...). They go through `GenerationAdapter` so the platform owns the provider
selection, token budget enforcement, retries, and observability.
"""

from ragent_python.core.generation.adapter import (
    GenerationAdapter,
    GenerationChunk,
    GenerationFinishReason,
    GenerationRequest,
    GenerationResult,
    GenerationMessage,
)

__all__ = [
    "GenerationAdapter",
    "GenerationChunk",
    "GenerationFinishReason",
    "GenerationMessage",
    "GenerationRequest",
    "GenerationResult",
]
