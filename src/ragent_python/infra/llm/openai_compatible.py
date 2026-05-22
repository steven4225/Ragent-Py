"""Vendor-agnostic OpenAI-compatible GenerationAdapter.

The OpenAI SDK accepts a `base_url` override, so any service that
implements OpenAI's `/v1/chat/completions` contract can be driven by
this one adapter: OpenAI's own endpoint, Alibaba Cloud DashScope
(`https://dashscope.aliyuncs.com/compatible-mode/v1`), Moonshot,
DeepSeek, SiliconFlow, self-hosted vLLM / SGLang, etc. The Python side
does not bind to any specific vendor's name; it picks one provider per
process via env (`OPENAI_BASE_URL`, `OPENAI_API_KEY`,
`PYTHON_LLM_MODEL`).

`is_available()` returns False when either the SDK is not installed or
no API key is configured, so the resolver can fall through to the next
provider in the chain (terminally `mock`). All errors during a
`generate()` call surface as `GenerationResult(finish_reason="error")`
rather than raising, so the calling module can degrade gracefully.
"""

from __future__ import annotations

from typing import AsyncIterator

from ragent_python.config import get_settings
from ragent_python.core.generation.adapter import (
    GenerationChunk,
    GenerationRequest,
    GenerationResult,
)


try:  # the SDK is a hard dependency in pyproject.toml, but keep this defensive
    from openai import AsyncOpenAI
    from openai import APIError, APITimeoutError

    _OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover - only triggered if dep is removed
    AsyncOpenAI = None  # type: ignore[assignment]
    APIError = Exception  # type: ignore[assignment, misc]
    APITimeoutError = Exception  # type: ignore[assignment, misc]
    _OPENAI_AVAILABLE = False


DEFAULT_MODEL = "gpt-4o-mini"


class OpenAICompatibleGenerationAdapter:
    """Adapter for any OpenAI `/v1/chat/completions`-compatible service."""

    name = "openai_compatible"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        request_timeout_seconds: float = 30.0,
    ) -> None:
        settings = get_settings()
        self._api_key = (api_key if api_key is not None else settings.openai_api_key).strip()
        self._base_url = (
            base_url if base_url is not None else settings.openai_base_url
        ).strip() or None
        self._model = (
            model if model is not None else settings.llm_model
        ).strip() or DEFAULT_MODEL
        self._request_timeout_seconds = request_timeout_seconds
        self._client: AsyncOpenAI | None = None

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str | None:
        return self._base_url

    def is_available(self) -> bool:
        return bool(_OPENAI_AVAILABLE and self._api_key)

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            assert AsyncOpenAI is not None  # narrowed by is_available()
            kwargs: dict[str, object] = {
                "api_key": self._api_key,
                "timeout": self._request_timeout_seconds,
            }
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    @staticmethod
    def _to_openai_messages(request: GenerationRequest) -> list[dict[str, str]]:
        return [
            {"role": message.role, "content": message.content}
            for message in request.messages
            if message.role in ("system", "user", "assistant")
        ]

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if not self.is_available():
            return GenerationResult(
                text="",
                finish_reason="error",
                provider=self.name,
                model=self._model,
                metadata={
                    "error": "OpenAI-compatible adapter unavailable: missing API key or SDK.",
                },
            )
        client = self._get_client()
        model_for_request = request.model_hint or self._model
        try:
            completion = await client.chat.completions.create(
                model=model_for_request,
                messages=self._to_openai_messages(request),
                temperature=request.temperature,
                max_tokens=request.max_output_tokens,
                stop=request.stop or None,
            )
        except APITimeoutError as exc:
            return GenerationResult(
                text="",
                finish_reason="error",
                provider=self.name,
                model=model_for_request,
                metadata={"error": f"timeout: {exc}"},
            )
        except APIError as exc:  # network / 4xx / 5xx
            return GenerationResult(
                text="",
                finish_reason="error",
                provider=self.name,
                model=model_for_request,
                metadata={"error": f"api_error: {exc}"},
            )

        choice = completion.choices[0] if completion.choices else None
        text = (choice.message.content or "") if choice and choice.message else ""
        finish_reason_raw = choice.finish_reason if choice else None
        finish_reason: str = "stop"
        if finish_reason_raw == "length":
            finish_reason = "length"
        elif finish_reason_raw == "tool_calls":
            finish_reason = "tool_call"
        elif finish_reason_raw == "content_filter":
            finish_reason = "content_filter"

        usage = getattr(completion, "usage", None)
        return GenerationResult(
            text=text,
            finish_reason=finish_reason,  # type: ignore[arg-type]
            provider=self.name,
            model=getattr(completion, "model", model_for_request) or model_for_request,
            input_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
            output_tokens=getattr(usage, "completion_tokens", None) if usage else None,
            metadata={
                "base_url": self._base_url or "(default)",
                "completion_id": getattr(completion, "id", None),
            },
        )

    async def stream(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        # Streaming is deliberately implemented as a fallback to non-stream
        # generate(); the preview endpoint does not need real SSE in this
        # push, and keeping a single network path simplifies error mapping.
        result = await self.generate(request)
        yield GenerationChunk(delta=result.text, finish_reason=result.finish_reason)
