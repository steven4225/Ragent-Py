"""`/internal/chat/router/stream` — the controlled ecommerce-aware entry
point.

The router endpoint is *not* an interceptor on the main chat stream.
It is a new endpoint the BFF (`web/app/api/chat/stream/route.ts`)
calls when the user has explicitly turned on "Ecommerce mode" in the
chat UI. With the toggle off, the BFF keeps calling
`/internal/chat/stream` unchanged and this endpoint is never reached.

Dispatch table (mode is an explicit field on the request, not inferred
from the message body):

| `mode`         | classifier outcome      | downstream                                       |
| -------------- | ----------------------- | ------------------------------------------------ |
| `"ecommerce"`  | matches ecommerce       | `iter_ecommerce_router_stream_events` (LLM lane) |
| `"ecommerce"`  | no match                | `iter_chat_stream_events` (default chat)         |
| `"default"`    | (classifier skipped)    | `iter_chat_stream_events` (default chat)         |

`services/chat_service.py` is **not modified**. We call its public
`iter_chat_stream_events` generator the same way `/internal/chat/stream`
calls it. The ecommerce branch never touches chat_service at all.

The classifier itself is keyword-only (see
`core/router/intent_router.py`) so this endpoint adds at most ~tens
of microseconds of overhead even on the cold path.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Iterator, Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ragent_python.contracts.internal_api import InternalChatRequestModel
from ragent_python.core.router.intent_router import (
    IntentRouter,
    default_intent_router,
)
from ragent_python.infra.llm.resolver import resolve_generation_adapter
from ragent_python.modules.ecommerce.chat_stream_bridge import (
    iter_ecommerce_router_stream_events,
)
from ragent_python.services.chat_service import iter_chat_stream_events


router = APIRouter(prefix="/internal/chat/router", tags=["chat"])


RoutingMode = Literal["ecommerce", "default"]


class InternalChatRouterRequest(InternalChatRequestModel):
    mode: RoutingMode = "default"


class InternalChatRouterDecisionResponse(BaseModel):
    """Inspection-only — returns the classifier verdict without
    actually running the stream. Useful for the admin debug UI and
    for tests that want to assert routing decisions without exercising
    an LLM adapter.
    """

    mode: RoutingMode
    routed_to: Literal["ecommerce", "default"]
    intent: str | None
    matched_intents: list[str]


def build_router_decision(
    request: InternalChatRouterRequest,
    *,
    intent_router: IntentRouter | None = None,
) -> InternalChatRouterDecisionResponse:
    router_instance = intent_router or default_intent_router
    if request.mode == "ecommerce":
        decision = router_instance.classify_for_module(
            request.message, module="ecommerce"
        )
        return InternalChatRouterDecisionResponse(
            mode=request.mode,
            routed_to="ecommerce" if decision.is_match else "default",
            intent=decision.intent,
            matched_intents=[p.name for p in decision.matched],
        )
    return InternalChatRouterDecisionResponse(
        mode=request.mode,
        routed_to="default",
        intent=None,
        matched_intents=[],
    )


@router.post("/decision", response_model=InternalChatRouterDecisionResponse)
async def internal_chat_router_decision(
    request: InternalChatRouterRequest,
) -> InternalChatRouterDecisionResponse:
    return build_router_decision(request)


def _sync_iterator_to_async(it: Iterator[str]) -> AsyncIterator[str]:
    async def _async_gen() -> AsyncIterator[str]:
        for line in it:
            yield line
            await asyncio.sleep(0)

    return _async_gen()


async def _iter_router_ndjson(
    request: InternalChatRouterRequest,
    intent_router: IntentRouter,
) -> AsyncIterator[str]:
    if request.mode == "ecommerce":
        decision = intent_router.classify_for_module(
            request.message, module="ecommerce"
        )
        if decision.is_match and decision.intent is not None:
            adapter = resolve_generation_adapter()
            async for line in iter_ecommerce_router_stream_events(
                request, adapter=adapter, intent=decision.intent
            ):
                yield line
            return

    async for line in _sync_iterator_to_async(iter_chat_stream_events(request)):
        yield line


@router.post("/stream")
async def internal_chat_router_stream(
    request: InternalChatRouterRequest,
) -> StreamingResponse:
    return StreamingResponse(
        _iter_router_ndjson(request, default_intent_router),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
