"""Tests for the ecommerce-aware chat router (`/internal/chat/router`).

The router is the controlled entry point that the main chat UI calls
when the user has explicitly turned on "Ecommerce mode". These tests
exercise four layers in isolation:

1. `IntentRouter` against an in-memory `IntentPatternRegistry`
2. `build_ecommerce_intent_patterns()` keyword precision/recall
3. `iter_ecommerce_router_stream_events` translation (ecommerce NDJSON
   → main chat protocol)
4. `/internal/chat/router/decision` and `/internal/chat/router/stream`
   endpoint contracts

`services/chat_service.py` is exercised through its existing public
generator only — these tests do not modify it and only verify that
the router falls back to it cleanly when the classifier says no.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from typing import AsyncIterator

from fastapi.testclient import TestClient

from ragent_python.api.internal_chat_router import (
    InternalChatRouterRequest,
    build_router_decision,
)
from ragent_python.core.generation.adapter import (
    GenerationAdapter,
    GenerationChunk,
    GenerationRequest,
    GenerationResult,
)
from ragent_python.core.router.intent import IntentPattern
from ragent_python.core.router.intent_router import IntentRouter
from ragent_python.infra.registries.intent_pattern import IntentPatternRegistry
from ragent_python.main import create_app
from ragent_python.modules.ecommerce.chat_stream_bridge import (
    iter_ecommerce_router_stream_events,
)
from ragent_python.modules.ecommerce.intent import build_ecommerce_intent_patterns
from ragent_python.contracts.internal_api import InternalChatRequestModel


class StubAdapter(GenerationAdapter):
    name = "stub"
    model = "stub-model"

    def __init__(self, deltas: tuple[str, ...] = ("Hello", " world"), finish_reason: str = "stop") -> None:
        self._deltas = deltas
        self._finish_reason = finish_reason

    def is_available(self) -> bool:
        return True

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        return GenerationResult(
            text="".join(self._deltas),
            provider=self.name,
            model=self.model,
            finish_reason=self._finish_reason,
            input_tokens=None,
            output_tokens=None,
        )

    async def stream(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        for index, delta in enumerate(self._deltas):
            yield GenerationChunk(
                delta=delta,
                finish_reason=self._finish_reason if index == len(self._deltas) - 1 else None,
            )


def _build_registry_with_patterns(*patterns: IntentPattern) -> IntentPatternRegistry:
    registry = IntentPatternRegistry()
    for pattern in patterns:
        registry.register(pattern)
    return registry


def _run_async(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class IntentRouterTests(unittest.TestCase):
    def test_classify_returns_no_match_when_registry_empty(self) -> None:
        router = IntentRouter(registry=IntentPatternRegistry())
        decision = router.classify("recommend me a laptop")
        self.assertIsNone(decision.intent)
        self.assertIsNone(decision.module)
        self.assertEqual(decision.matched, ())
        self.assertFalse(decision.is_match)

    def test_classify_picks_highest_weight(self) -> None:
        patterns = (
            IntentPattern(
                name="low",
                module="mod_a",
                keywords=("laptop",),
                weight=1.0,
            ),
            IntentPattern(
                name="high",
                module="mod_a",
                keywords=("laptop",),
                weight=5.0,
            ),
        )
        registry = _build_registry_with_patterns(*patterns)
        router = IntentRouter(registry=registry)
        decision = router.classify("buy a laptop please")
        self.assertEqual(decision.intent, "high")
        self.assertEqual(decision.matched[0].name, "high")
        self.assertEqual(decision.matched[1].name, "low")

    def test_classify_for_module_filters_out_other_modules(self) -> None:
        patterns = (
            IntentPattern(
                name="other.buy",
                module="other",
                keywords=("buy",),
                weight=10.0,
            ),
            IntentPattern(
                name="ecommerce.consult",
                module="ecommerce",
                keywords=("laptop",),
                weight=1.0,
            ),
        )
        registry = _build_registry_with_patterns(*patterns)
        router = IntentRouter(registry=registry)
        decision = router.classify_for_module(
            "buy a laptop please",
            module="ecommerce",
        )
        self.assertEqual(decision.intent, "ecommerce.consult")
        self.assertEqual(decision.module, "ecommerce")

    def test_classify_for_module_returns_no_match_when_no_owner_matches(self) -> None:
        patterns = (
            IntentPattern(
                name="other.buy",
                module="other",
                keywords=("buy",),
                weight=10.0,
            ),
        )
        registry = _build_registry_with_patterns(*patterns)
        router = IntentRouter(registry=registry)
        decision = router.classify_for_module(
            "buy this thing",
            module="ecommerce",
        )
        self.assertFalse(decision.is_match)


class EcommerceIntentPatternsTests(unittest.TestCase):
    """Keyword precision/recall on representative real-world queries."""

    def setUp(self) -> None:
        self.registry = _build_registry_with_patterns(
            *build_ecommerce_intent_patterns()
        )
        self.router = IntentRouter(registry=self.registry)

    def _route(self, query: str) -> str | None:
        decision = self.router.classify_for_module(query, module="ecommerce")
        return decision.intent

    def test_recommend_laptop_matches_consult(self) -> None:
        self.assertEqual(
            self._route("recommend a laptop under 1500 dollars"),
            "ecommerce.product_consult",
        )

    def test_compare_two_phones_matches_compare(self) -> None:
        self.assertEqual(
            self._route("compare iphone 15 vs pixel 9"),
            "ecommerce.product_compare",
        )

    def test_buy_verb_matches_buy_intent(self) -> None:
        self.assertEqual(
            self._route("I want to buy a tablet for my mom"),
            "ecommerce.product_buy",
        )

    def test_chinese_keywords_match_consult(self) -> None:
        self.assertEqual(
            self._route("推荐一款笔记本电脑，预算两千"),
            "ecommerce.product_consult",
        )

    def test_false_positive_excluded(self) -> None:
        """Generic technical chatter should NOT match."""
        for query in (
            "how do I fix a TypeScript error?",
            "what is the capital of France?",
            "my computer crashed, can you help me debug it?",
        ):
            with self.subTest(query=query):
                self.assertIsNone(self._route(query))

    def test_weight_order_is_buy_then_compare_then_consult(self) -> None:
        patterns = build_ecommerce_intent_patterns()
        weights = {pattern.name: pattern.weight for pattern in patterns}
        self.assertGreater(weights["ecommerce.product_buy"], weights["ecommerce.product_compare"])
        self.assertGreater(weights["ecommerce.product_compare"], weights["ecommerce.product_consult"])


class EcommerceStreamBridgeTests(unittest.TestCase):
    """The bridge must translate to main chat protocol exactly."""

    def _collect(self, request: InternalChatRequestModel, adapter: GenerationAdapter) -> list[dict]:
        async def _run() -> list[dict]:
            events: list[dict] = []
            async for line in iter_ecommerce_router_stream_events(
                request, adapter=adapter
            ):
                events.append(json.loads(line))
            return events

        return _run_async(_run())

    def test_emits_main_protocol_event_sequence(self) -> None:
        request = InternalChatRequestModel(
            message="recommend a laptop under 1500 dollars",
            conversationId="conv_test_bridge",
            userId="user_test",
            tenantId="tenant_test",
            orgId=None,
            role="user",
        )
        adapter = StubAdapter(deltas=("First part. ", "Second part."))
        events = self._collect(request, adapter)
        types = [event["type"] for event in events]

        self.assertEqual(types[0], "chat.started")
        self.assertIn("thinking.delta", types)
        self.assertIn("thinking.completed", types)
        self.assertIn("message.delta", types)
        self.assertEqual(types[-2], "message.completed")
        self.assertEqual(types[-1], "chat.completed")

    def test_message_completed_carries_blocks_in_metadata(self) -> None:
        request = InternalChatRequestModel(
            message="recommend a laptop under 1500 dollars",
            conversationId="conv_test_bridge_blocks",
            userId="user_test",
            tenantId="tenant_test",
            orgId=None,
            role="user",
        )
        adapter = StubAdapter()
        events = self._collect(request, adapter)
        completed = next(event for event in events if event["type"] == "message.completed")
        assistant = completed["assistantMessage"]
        self.assertEqual(assistant["role"], "assistant")
        self.assertIn("blocks", assistant["metadata"])
        blocks = assistant["metadata"]["blocks"]
        self.assertIsInstance(blocks, list)
        if blocks:
            self.assertEqual(blocks[0]["type"], "product_card")
        self.assertIn("retrieval", assistant["metadata"])
        self.assertIn("generation", assistant["metadata"])

    def test_message_delta_text_concatenates_into_final_content(self) -> None:
        request = InternalChatRequestModel(
            message="recommend a laptop",
            conversationId="conv_test_bridge_concat",
            userId="user_test",
            tenantId="tenant_test",
            orgId=None,
            role="user",
        )
        adapter = StubAdapter(deltas=("Alpha. ", "Beta. ", "Gamma."))
        events = self._collect(request, adapter)
        deltas = [event["delta"] for event in events if event["type"] == "message.delta"]
        self.assertEqual("".join(deltas), "Alpha. Beta. Gamma.")
        completed = next(event for event in events if event["type"] == "message.completed")
        self.assertEqual(completed["assistantMessage"]["content"], "Alpha. Beta. Gamma.")

    def test_chat_completed_marks_use_retrieval(self) -> None:
        request = InternalChatRequestModel(
            message="recommend a laptop",
            conversationId="conv_test_bridge_plan",
            userId="user_test",
            tenantId="tenant_test",
            orgId=None,
            role="user",
        )
        adapter = StubAdapter()
        events = self._collect(request, adapter)
        completed = next(event for event in events if event["type"] == "chat.completed")
        self.assertTrue(completed["plan"]["useRetrieval"])
        self.assertFalse(completed["plan"]["useTools"])


class ChatRouterDecisionLogicTests(unittest.TestCase):
    """The plain-function decision builder used by the /decision endpoint."""

    def test_default_mode_skips_classifier(self) -> None:
        request = InternalChatRouterRequest(
            message="recommend a laptop please",
            conversationId="conv_decision_default",
            userId="user_t",
            tenantId="tenant_t",
            mode="default",
        )
        decision = build_router_decision(request)
        self.assertEqual(decision.mode, "default")
        self.assertEqual(decision.routed_to, "default")
        self.assertIsNone(decision.intent)
        self.assertEqual(decision.matched_intents, [])

    def test_ecommerce_mode_with_matching_intent_routes_to_ecommerce(self) -> None:
        registry = _build_registry_with_patterns(
            *build_ecommerce_intent_patterns()
        )
        router = IntentRouter(registry=registry)
        request = InternalChatRouterRequest(
            message="compare iphone 15 vs pixel 9",
            conversationId="conv_decision_ecom",
            userId="user_t",
            tenantId="tenant_t",
            mode="ecommerce",
        )
        decision = build_router_decision(request, intent_router=router)
        self.assertEqual(decision.routed_to, "ecommerce")
        self.assertEqual(decision.intent, "ecommerce.product_compare")

    def test_ecommerce_mode_with_no_intent_falls_back_to_default(self) -> None:
        registry = _build_registry_with_patterns(
            *build_ecommerce_intent_patterns()
        )
        router = IntentRouter(registry=registry)
        request = InternalChatRouterRequest(
            message="how do I fix a TypeScript error?",
            conversationId="conv_decision_fallback",
            userId="user_t",
            tenantId="tenant_t",
            mode="ecommerce",
        )
        decision = build_router_decision(request, intent_router=router)
        self.assertEqual(decision.routed_to, "default")
        self.assertIsNone(decision.intent)


class InternalChatRouterEndpointTests(unittest.TestCase):
    """End-to-end FastAPI tests against the wired-up endpoints."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(create_app())

    def test_decision_endpoint_returns_routing_envelope(self) -> None:
        response = self.client.post(
            "/internal/chat/router/decision",
            json={
                "message": "buy me a laptop please",
                "conversationId": "conv_e2e_decision",
                "userId": "user_e2e",
                "tenantId": "tenant_e2e",
                "mode": "ecommerce",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["mode"], "ecommerce")
        self.assertEqual(body["routed_to"], "ecommerce")
        self.assertEqual(body["intent"], "ecommerce.product_buy")
        self.assertIn("ecommerce.product_buy", body["matched_intents"])

    def test_decision_endpoint_default_mode_skips_classifier(self) -> None:
        response = self.client.post(
            "/internal/chat/router/decision",
            json={
                "message": "buy me a laptop please",
                "conversationId": "conv_e2e_decision_def",
                "userId": "user_e2e",
                "tenantId": "tenant_e2e",
                "mode": "default",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["mode"], "default")
        self.assertEqual(body["routed_to"], "default")
        self.assertIsNone(body["intent"])

    def test_stream_endpoint_default_mode_delegates_to_chat_service(self) -> None:
        """Default mode must produce the same protocol as
        /internal/chat/stream — i.e. the existing chat_service path,
        which the router does NOT modify."""

        response = self.client.post(
            "/internal/chat/router/stream",
            json={
                "message": "hello world",
                "conversationId": "conv_e2e_default_stream",
                "userId": "user_e2e",
                "tenantId": "tenant_e2e",
                "mode": "default",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["content-type"].split(";")[0],
            "application/x-ndjson",
        )
        lines = [line for line in response.text.split("\n") if line.strip()]
        events = [json.loads(line) for line in lines]
        types = [event["type"] for event in events]
        self.assertEqual(types[0], "chat.started")
        self.assertEqual(types[-1], "chat.completed")

    def test_stream_endpoint_ecommerce_mode_with_match_uses_ecommerce_lane(self) -> None:
        """Ecommerce mode + ecommerce intent → ecommerce lane, but
        still emits main protocol events (translated by the bridge)."""

        response = self.client.post(
            "/internal/chat/router/stream",
            json={
                "message": "recommend a laptop under 1500 dollars",
                "conversationId": "conv_e2e_ecom_stream",
                "userId": "user_e2e",
                "tenantId": "tenant_e2e",
                "mode": "ecommerce",
            },
        )
        self.assertEqual(response.status_code, 200)
        lines = [line for line in response.text.split("\n") if line.strip()]
        events = [json.loads(line) for line in lines]
        types = [event["type"] for event in events]
        self.assertEqual(types[0], "chat.started")
        self.assertEqual(types[-1], "chat.completed")
        completed = next(event for event in events if event["type"] == "message.completed")
        self.assertIn("blocks", completed["assistantMessage"]["metadata"])
        self.assertIn("retrieval", completed["assistantMessage"]["metadata"])

    def test_stream_endpoint_ecommerce_mode_no_match_falls_back_to_chat_service(self) -> None:
        """Ecommerce mode + non-ecommerce query → falls back to
        chat_service, identical to /internal/chat/stream output."""

        response = self.client.post(
            "/internal/chat/router/stream",
            json={
                "message": "what is the capital of France?",
                "conversationId": "conv_e2e_ecom_fallback",
                "userId": "user_e2e",
                "tenantId": "tenant_e2e",
                "mode": "ecommerce",
            },
        )
        self.assertEqual(response.status_code, 200)
        lines = [line for line in response.text.split("\n") if line.strip()]
        events = [json.loads(line) for line in lines]
        types = [event["type"] for event in events]
        self.assertEqual(types[0], "chat.started")
        self.assertEqual(types[-1], "chat.completed")
        # The fallback lane does not surface ecommerce blocks.
        completed = next(event for event in events if event["type"] == "message.completed")
        self.assertNotIn(
            "blocks",
            completed.get("assistantMessage", {}).get("metadata", {}),
        )


if __name__ == "__main__":
    unittest.main()
