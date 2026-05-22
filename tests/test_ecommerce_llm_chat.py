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
    build_chat_request,
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


if __name__ == "__main__":
    unittest.main()
