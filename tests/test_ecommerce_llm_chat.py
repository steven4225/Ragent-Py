from __future__ import annotations

import asyncio
import os
import unittest
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from ragent_python.config import get_settings
from ragent_python.core.generation.adapter import (
    GenerationMessage,
    GenerationRequest,
    GenerationResult,
)
from ragent_python.infra.llm.mock import MockGenerationAdapter
from ragent_python.infra.llm.openai_compatible import (
    DEFAULT_MODEL,
    OpenAICompatibleGenerationAdapter,
)
from ragent_python.infra.llm.resolver import (
    clear_resolver_cache,
    list_known_providers,
    resolve_generation_adapter,
)
from ragent_python.main import create_app
from ragent_python.modules.ecommerce.catalog import load_products, search_products
from ragent_python.modules.ecommerce.chat import (
    EcommerceChatDeltaEvent,
    EcommerceChatDoneEvent,
    EcommerceChatRetrievalEvent,
    build_chat_request,
    run_ecommerce_chat_stream,
    run_ecommerce_chat_turn,
)


def _run(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


def _reset_settings_cache() -> None:
    get_settings.cache_clear()
    clear_resolver_cache()


def _settings_env(**overrides: str) -> dict[str, str]:
    base = {
        "PYTHON_LLM_PROVIDER": "auto",
        "PYTHON_LLM_FALLBACK_CHAIN": "openai,mock",
        "PYTHON_LLM_MODEL": "",
        "OPENAI_API_KEY": "",
        "OPENAI_BASE_URL": "",
    }
    base.update(overrides)
    return base


class OpenAICompatibleAvailabilityTests(unittest.TestCase):
    def tearDown(self) -> None:
        _reset_settings_cache()

    def test_unavailable_without_api_key(self) -> None:
        with patch.dict(os.environ, _settings_env(), clear=False):
            _reset_settings_cache()
            adapter = OpenAICompatibleGenerationAdapter()
            self.assertFalse(adapter.is_available())

    def test_available_when_api_key_present(self) -> None:
        with patch.dict(os.environ, _settings_env(OPENAI_API_KEY="sk-test-123"), clear=False):
            _reset_settings_cache()
            adapter = OpenAICompatibleGenerationAdapter()
            self.assertTrue(adapter.is_available())

    def test_returns_error_result_when_unavailable(self) -> None:
        with patch.dict(os.environ, _settings_env(), clear=False):
            _reset_settings_cache()
            adapter = OpenAICompatibleGenerationAdapter()
            request = GenerationRequest(
                messages=[GenerationMessage(role="user", content="hi")]
            )
            result = asyncio.run(adapter.generate(request))
            self.assertEqual(result.finish_reason, "error")
            self.assertEqual(result.provider, "openai_compatible")
            self.assertEqual(result.text, "")
            self.assertIn("error", result.metadata)

    def test_default_model_when_setting_blank(self) -> None:
        with patch.dict(os.environ, _settings_env(OPENAI_API_KEY="sk-x"), clear=False):
            _reset_settings_cache()
            adapter = OpenAICompatibleGenerationAdapter()
            self.assertEqual(adapter.model, DEFAULT_MODEL)

    def test_explicit_constructor_overrides_settings(self) -> None:
        with patch.dict(os.environ, _settings_env(), clear=False):
            _reset_settings_cache()
            adapter = OpenAICompatibleGenerationAdapter(
                api_key="sk-explicit",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                model="qwen-plus",
            )
            self.assertTrue(adapter.is_available())
            self.assertEqual(adapter.model, "qwen-plus")
            self.assertEqual(
                adapter.base_url,
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            )


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str, finish_reason: str = "stop") -> None:
        self.message = _FakeMessage(content)
        self.finish_reason = finish_reason


class _FakeUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeCompletion:
    def __init__(
        self,
        content: str,
        finish_reason: str = "stop",
        prompt_tokens: int = 12,
        completion_tokens: int = 7,
        model: str = "fake-model",
    ) -> None:
        self.choices = [_FakeChoice(content, finish_reason)]
        self.usage = _FakeUsage(prompt_tokens, completion_tokens)
        self.model = model
        self.id = "cmpl-fake"


class _FakeCompletions:
    def __init__(self, completion: _FakeCompletion, recorder: dict[str, Any]) -> None:
        self._completion = completion
        self._recorder = recorder

    async def create(self, **kwargs: Any) -> _FakeCompletion:
        self._recorder.update(kwargs)
        return self._completion


class _FakeChatNamespace:
    def __init__(self, completion: _FakeCompletion, recorder: dict[str, Any]) -> None:
        self.completions = _FakeCompletions(completion, recorder)


class _FakeAsyncOpenAI:
    def __init__(self, completion: _FakeCompletion, recorder: dict[str, Any]) -> None:
        self.chat = _FakeChatNamespace(completion, recorder)


class OpenAICompatibleGenerateTests(unittest.TestCase):
    def tearDown(self) -> None:
        _reset_settings_cache()

    def test_generate_maps_completion_to_result(self) -> None:
        recorder: dict[str, Any] = {}
        fake_completion = _FakeCompletion(
            "Recommended: MacBook Pro 14",
            finish_reason="stop",
            prompt_tokens=120,
            completion_tokens=22,
            model="qwen-plus",
        )
        with patch.dict(
            os.environ,
            _settings_env(
                OPENAI_API_KEY="sk-fake",
                OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1",
                PYTHON_LLM_MODEL="qwen-plus",
            ),
            clear=False,
        ):
            _reset_settings_cache()
            adapter = OpenAICompatibleGenerationAdapter()
            adapter._client = _FakeAsyncOpenAI(fake_completion, recorder)  # type: ignore[assignment]
            request = GenerationRequest(
                messages=[
                    GenerationMessage(role="system", content="be concise"),
                    GenerationMessage(role="user", content="recommend a laptop"),
                ],
                temperature=0.1,
                max_output_tokens=256,
            )
            result = asyncio.run(adapter.generate(request))
            self.assertEqual(result.provider, "openai_compatible")
            self.assertEqual(result.text, "Recommended: MacBook Pro 14")
            self.assertEqual(result.finish_reason, "stop")
            self.assertEqual(result.input_tokens, 120)
            self.assertEqual(result.output_tokens, 22)
            self.assertEqual(result.model, "qwen-plus")
            self.assertEqual(recorder["model"], "qwen-plus")
            self.assertEqual(recorder["temperature"], 0.1)
            self.assertEqual(recorder["max_tokens"], 256)
            self.assertEqual(
                recorder["messages"],
                [
                    {"role": "system", "content": "be concise"},
                    {"role": "user", "content": "recommend a laptop"},
                ],
            )

    def test_generate_maps_length_finish_reason(self) -> None:
        recorder: dict[str, Any] = {}
        fake_completion = _FakeCompletion("partial", finish_reason="length")
        with patch.dict(
            os.environ,
            _settings_env(OPENAI_API_KEY="sk-fake", PYTHON_LLM_MODEL="qwen-plus"),
            clear=False,
        ):
            _reset_settings_cache()
            adapter = OpenAICompatibleGenerationAdapter()
            adapter._client = _FakeAsyncOpenAI(fake_completion, recorder)  # type: ignore[assignment]
            result = asyncio.run(
                adapter.generate(
                    GenerationRequest(
                        messages=[GenerationMessage(role="user", content="hello")]
                    )
                )
            )
            self.assertEqual(result.finish_reason, "length")


class ResolverTests(unittest.TestCase):
    def tearDown(self) -> None:
        _reset_settings_cache()

    def test_known_providers_include_openai_aliases(self) -> None:
        providers = list_known_providers()
        self.assertIn("mock", providers)
        self.assertIn("openai", providers)
        self.assertIn("openai_compatible", providers)

    def test_falls_back_to_mock_when_no_key(self) -> None:
        with patch.dict(os.environ, _settings_env(), clear=False):
            _reset_settings_cache()
            adapter = resolve_generation_adapter()
            self.assertIsInstance(adapter, MockGenerationAdapter)

    def test_resolves_openai_compatible_when_key_present(self) -> None:
        with patch.dict(
            os.environ,
            _settings_env(OPENAI_API_KEY="sk-test", PYTHON_LLM_MODEL="qwen-plus"),
            clear=False,
        ):
            _reset_settings_cache()
            adapter = resolve_generation_adapter()
            self.assertEqual(adapter.name, "openai_compatible")

    def test_explicit_provider_overrides_chain(self) -> None:
        with patch.dict(
            os.environ,
            _settings_env(
                PYTHON_LLM_PROVIDER="mock",
                OPENAI_API_KEY="sk-test",
            ),
            clear=False,
        ):
            _reset_settings_cache()
            adapter = resolve_generation_adapter()
            self.assertIsInstance(adapter, MockGenerationAdapter)


class EcommerceChatOrchestrationTests(unittest.TestCase):
    def tearDown(self) -> None:
        _reset_settings_cache()

    def test_build_chat_request_inlines_candidate_products(self) -> None:
        products = search_products("macbook", limit=2)
        request = build_chat_request("recommend a laptop", products)
        self.assertEqual(len(request.messages), 2)
        system = request.messages[0]
        user = request.messages[1]
        self.assertEqual(system.role, "system")
        self.assertEqual(user.role, "user")
        self.assertEqual(user.content, "recommend a laptop")
        for product in products:
            self.assertIn(product.product_id, system.content)
            self.assertIn(product.name, system.content)

    def test_build_chat_request_handles_no_candidates(self) -> None:
        request = build_chat_request("recommend a laptop", [])
        self.assertIn("(no candidate products matched", request.messages[0].content)

    def test_run_ecommerce_chat_turn_with_mock_adapter(self) -> None:
        turn = asyncio.run(
            run_ecommerce_chat_turn(
                "recommend a laptop under 1500",
                adapter=MockGenerationAdapter(),
                retrieval_limit=3,
            )
        )
        self.assertEqual(turn.query, "recommend a laptop under 1500")
        self.assertEqual(turn.answer.provider, "mock")
        self.assertGreaterEqual(len(turn.retrieved_products), 1)
        self.assertEqual(len(turn.blocks), len(turn.retrieved_products))
        for block in turn.blocks:
            self.assertEqual(block.type, "product_card")

    def test_run_ecommerce_chat_turn_with_error_adapter_returns_error_result(self) -> None:
        class _ErrorAdapter:
            name = "broken_provider"

            def is_available(self) -> bool:
                return True

            async def generate(self, request: GenerationRequest) -> GenerationResult:
                return GenerationResult(
                    text="",
                    finish_reason="error",
                    provider=self.name,
                    model="broken",
                    metadata={"error": "boom"},
                )

            async def stream(self, request: GenerationRequest):
                yield  # pragma: no cover

        turn = asyncio.run(
            run_ecommerce_chat_turn(
                "any query",
                adapter=_ErrorAdapter(),  # type: ignore[arg-type]
                retrieval_limit=2,
            )
        )
        self.assertEqual(turn.answer.finish_reason, "error")
        self.assertEqual(turn.answer.provider, "broken_provider")


class InternalEcommerceChatEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_settings_cache()
        with patch.dict(os.environ, _settings_env(), clear=False):
            _reset_settings_cache()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        _reset_settings_cache()

    def test_chat_returns_blocks_and_answer(self) -> None:
        response = self.client.post(
            "/internal/ecommerce/chat",
            json={
                "query": "recommend a laptop under 1500",
                "filters": {"category": "laptop", "max_price_usd": 1500},
                "retrieval_limit": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["source"], "ecommerce-chat-preview")
        self.assertEqual(body["query"], "recommend a laptop under 1500")
        self.assertGreaterEqual(len(body["retrieved_product_ids"]), 1)
        self.assertEqual(len(body["blocks"]), len(body["retrieved_product_ids"]))
        for block in body["blocks"]:
            self.assertEqual(block["type"], "product_card")
            self.assertEqual(block["category"], "laptop")
        self.assertIn("answer", body)
        self.assertEqual(body["answer"]["provider"], "mock")
        self.assertIn("text", body["answer"])
        self.assertIn("finish_reason", body["answer"])

    def test_chat_empty_query_still_runs_against_recent_catalog(self) -> None:
        response = self.client.post(
            "/internal/ecommerce/chat",
            json={"query": "", "retrieval_limit": 4},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["query"], "")
        self.assertLessEqual(len(body["retrieved_product_ids"]), 4)


class _FakeStreamChoice:
    def __init__(self, content: str | None = None, finish_reason: str | None = None) -> None:
        self.delta = type("D", (), {"content": content})()
        self.finish_reason = finish_reason


class _FakeStreamEvent:
    def __init__(self, content: str | None = None, finish_reason: str | None = None) -> None:
        self.choices = [_FakeStreamChoice(content, finish_reason)]


class _FakeAsyncStream:
    def __init__(self, events: list[_FakeStreamEvent]) -> None:
        self._events = events

    def __aiter__(self) -> "_FakeAsyncStream":
        self._iter = iter(self._events)
        return self

    async def __anext__(self) -> _FakeStreamEvent:
        try:
            return next(self._iter)
        except StopIteration as stop:
            raise StopAsyncIteration from stop


class _FakeStreamingCompletions:
    def __init__(self, events: list[_FakeStreamEvent], recorder: dict[str, Any]) -> None:
        self._events = events
        self._recorder = recorder

    async def create(self, **kwargs: Any) -> _FakeAsyncStream:
        self._recorder.update(kwargs)
        return _FakeAsyncStream(self._events)


class _FakeStreamingChatNamespace:
    def __init__(self, events: list[_FakeStreamEvent], recorder: dict[str, Any]) -> None:
        self.completions = _FakeStreamingCompletions(events, recorder)


class _FakeStreamingAsyncOpenAI:
    def __init__(self, events: list[_FakeStreamEvent], recorder: dict[str, Any]) -> None:
        self.chat = _FakeStreamingChatNamespace(events, recorder)


class OpenAICompatibleStreamTests(unittest.TestCase):
    def tearDown(self) -> None:
        _reset_settings_cache()

    def test_stream_emits_deltas_and_final_finish(self) -> None:
        recorder: dict[str, Any] = {}
        events = [
            _FakeStreamEvent(content="Hel"),
            _FakeStreamEvent(content="lo"),
            _FakeStreamEvent(content=" world"),
            _FakeStreamEvent(content=None, finish_reason="stop"),
        ]
        with patch.dict(
            os.environ,
            _settings_env(OPENAI_API_KEY="sk-fake", PYTHON_LLM_MODEL="qwen-plus"),
            clear=False,
        ):
            _reset_settings_cache()
            adapter = OpenAICompatibleGenerationAdapter()
            adapter._client = _FakeStreamingAsyncOpenAI(events, recorder)  # type: ignore[assignment]

            async def _collect() -> list[Any]:
                out: list[Any] = []
                async for chunk in adapter.stream(
                    GenerationRequest(messages=[GenerationMessage(role="user", content="hi")])
                ):
                    out.append(chunk)
                return out

            chunks = asyncio.run(_collect())
            deltas = [c.delta for c in chunks if c.delta]
            self.assertEqual(deltas, ["Hel", "lo", " world"])
            self.assertTrue(recorder["stream"])
            self.assertEqual(chunks[-1].finish_reason, "stop")

    def test_stream_maps_length_finish(self) -> None:
        recorder: dict[str, Any] = {}
        events = [
            _FakeStreamEvent(content="too long"),
            _FakeStreamEvent(content=None, finish_reason="length"),
        ]
        with patch.dict(
            os.environ,
            _settings_env(OPENAI_API_KEY="sk-fake", PYTHON_LLM_MODEL="qwen-plus"),
            clear=False,
        ):
            _reset_settings_cache()
            adapter = OpenAICompatibleGenerationAdapter()
            adapter._client = _FakeStreamingAsyncOpenAI(events, recorder)  # type: ignore[assignment]

            async def _collect() -> list[Any]:
                out: list[Any] = []
                async for chunk in adapter.stream(
                    GenerationRequest(messages=[GenerationMessage(role="user", content="x")])
                ):
                    out.append(chunk)
                return out

            chunks = asyncio.run(_collect())
            self.assertEqual(chunks[-1].finish_reason, "length")

    def test_stream_yields_error_when_unavailable(self) -> None:
        with patch.dict(os.environ, _settings_env(), clear=False):
            _reset_settings_cache()
            adapter = OpenAICompatibleGenerationAdapter()

            async def _collect() -> list[Any]:
                out: list[Any] = []
                async for chunk in adapter.stream(
                    GenerationRequest(messages=[GenerationMessage(role="user", content="x")])
                ):
                    out.append(chunk)
                return out

            chunks = asyncio.run(_collect())
            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0].finish_reason, "error")


class EcommerceChatStreamOrchestrationTests(unittest.TestCase):
    def tearDown(self) -> None:
        _reset_settings_cache()

    def test_stream_emits_retrieval_then_deltas_then_done(self) -> None:
        async def _collect() -> list[Any]:
            out: list[Any] = []
            async for event in run_ecommerce_chat_stream(
                "recommend a laptop under 1500",
                adapter=MockGenerationAdapter(),
                retrieval_limit=3,
            ):
                out.append(event)
            return out

        events = asyncio.run(_collect())
        self.assertIsInstance(events[0], EcommerceChatRetrievalEvent)
        first = events[0]
        assert isinstance(first, EcommerceChatRetrievalEvent)
        self.assertGreaterEqual(len(first.blocks), 1)
        self.assertEqual(len(first.blocks), len(first.retrieved_product_ids))

        delta_events = [e for e in events if isinstance(e, EcommerceChatDeltaEvent)]
        self.assertGreaterEqual(len(delta_events), 2)

        last = events[-1]
        self.assertIsInstance(last, EcommerceChatDoneEvent)
        assert isinstance(last, EcommerceChatDoneEvent)
        self.assertEqual(last.provider, "mock")
        self.assertEqual(last.finish_reason, "stop")


class InternalEcommerceChatStreamEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_settings_cache()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        _reset_settings_cache()

    def test_stream_endpoint_returns_ndjson_with_expected_event_sequence(self) -> None:
        response = self.client.post(
            "/internal/ecommerce/chat/stream",
            json={
                "query": "recommend a laptop under 1500",
                "filters": {"category": "laptop", "max_price_usd": 1500},
                "retrieval_limit": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["content-type"].split(";")[0].strip(),
            "application/x-ndjson",
        )
        lines = [line for line in response.text.split("\n") if line.strip()]
        self.assertGreaterEqual(len(lines), 3)
        import json as _json

        parsed = [_json.loads(line) for line in lines]
        self.assertEqual(parsed[0]["type"], "retrieval")
        self.assertEqual(parsed[0]["query"], "recommend a laptop under 1500")
        self.assertGreaterEqual(len(parsed[0]["retrieved_product_ids"]), 1)
        self.assertEqual(
            len(parsed[0]["blocks"]), len(parsed[0]["retrieved_product_ids"])
        )
        for block in parsed[0]["blocks"]:
            self.assertEqual(block["type"], "product_card")
            self.assertEqual(block["category"], "laptop")
        delta_payloads = [evt for evt in parsed if evt["type"] == "delta"]
        self.assertGreaterEqual(len(delta_payloads), 1)
        self.assertEqual(parsed[-1]["type"], "done")
        self.assertEqual(parsed[-1]["provider"], "mock")
        self.assertEqual(parsed[-1]["finish_reason"], "stop")


if __name__ == "__main__":
    unittest.main()
