"""Translate the ecommerce NDJSON stream to the main chat stream protocol.

The ecommerce preview lane emits its own NDJSON event types
(`retrieval` / `delta` / `done`) — see
`modules/ecommerce/chat.run_ecommerce_chat_stream`. The main chat UI
in contrast consumes the protocol defined in
`contracts/public_api.py` (`chat.started`, `thinking.delta`,
`thinking.completed`, `message.delta`, `message.completed`,
`chat.completed`).

To make the ecommerce lane reusable from the main chat UI without
maintaining two parallel TS stream parsers, this bridge wraps
`run_ecommerce_chat_stream` and re-emits its output as main-protocol
events. The translation map:

| ecommerce event | main-protocol events emitted                                  |
| --------------- | ------------------------------------------------------------- |
| (start)         | `chat.started` (user message + conversation echoed back)      |
|                 | `thinking.delta` ("Searching the catalog…")                   |
| `retrieval`     | `thinking.delta` (one line per matched product, for trace)    |
|                 | `thinking.completed`                                          |
| `delta`         | `message.delta`                                               |
| `done`          | `message.completed` (assistantMessage carries answer text +   |
|                 |   `metadata.blocks = [ProductCardBlock, …]`)                  |
|                 | `chat.completed` (plan flags `useRetrieval=True`)             |

`metadata.blocks` is the contract knob the main chat UI uses to render
the `product_card` / `spec_compare` blocks below the assistant
message. The schema for `MessageModel.metadata` is `dict[str, Any]`
(see `contracts/public_api.MessageModel`), so this does not require
any protocol change on the BFF or UI side beyond a new renderer
branch on the existing `metadata` reader.

`services/chat_service.py` is untouched. This bridge does not import
it — it imports the public `ConversationModel` / `MessageModel`
contracts and emits the same NDJSON shape that `iter_chat_stream_events`
emits.
"""

from __future__ import annotations

from typing import AsyncIterator
from uuid import uuid4

from ragent_python.contracts.internal_api import InternalChatRequestModel
from ragent_python.contracts.public_api import (
    ChatCompletedEvent,
    ChatPlanModel,
    ChatStartedEvent,
    ConversationModel,
    MessageCompletedEvent,
    MessageDeltaEvent,
    MessageModel,
    ThinkingCompletedEvent,
    ThinkingDeltaEvent,
    utc_now_iso,
)
from ragent_python.core.generation.adapter import GenerationAdapter
from ragent_python.modules.ecommerce.chat import (
    EcommerceChatDeltaEvent,
    EcommerceChatDoneEvent,
    EcommerceChatRetrievalEvent,
    run_ecommerce_chat_stream,
)


def _make_trace_id() -> str:
    return f"trace_ecom_{uuid4().hex[:12]}"


def _make_message_id(role: str, trace_id: str) -> str:
    return f"msg_{role}_{trace_id}"


def _to_ndjson_line(model) -> str:
    return model.model_dump_json() + "\n"


async def iter_ecommerce_router_stream_events(
    request: InternalChatRequestModel,
    *,
    adapter: GenerationAdapter,
    retrieval_limit: int = 5,
) -> AsyncIterator[str]:
    """Run the ecommerce chat stream and emit main-protocol NDJSON lines.

    The output is byte-identical in shape to
    `iter_chat_stream_events()`'s output, so any consumer (BFF route,
    main chat UI) that already understands the main protocol will
    render this stream without protocol-specific code.
    """

    trace_id = _make_trace_id()
    conversation_id = request.conversationId or f"conv_router_{uuid4().hex[:10]}"

    conversation = ConversationModel(
        conversationId=conversation_id,
        userId=request.userId,
        orgId=request.orgId,
        tenantId=request.tenantId,
        title=conversation_id,
        summary="",
        lastSummarizedMessageId="",
        createdAt=utc_now_iso(),
        updatedAt=utc_now_iso(),
    )
    user_message = MessageModel(
        messageId=_make_message_id("user", trace_id),
        conversationId=conversation_id,
        role="user",
        content=request.message,
        metadata={},
        createdAt=utc_now_iso(),
    )

    yield _to_ndjson_line(
        ChatStartedEvent(
            traceId=trace_id,
            conversation=conversation,
            userMessage=user_message,
        )
    )
    yield _to_ndjson_line(
        ThinkingDeltaEvent(
            traceId=trace_id,
            delta="Searching the ecommerce catalog…",
        )
    )

    answer_buffer: list[str] = []
    retrieval_blocks: list[dict] = []
    retrieval_ids: list[str] = []
    final_provider = "unknown"
    final_model: str | None = None
    final_finish_reason = "stop"
    final_input_tokens: int | None = None
    final_output_tokens: int | None = None
    thinking_closed = False

    async for event in run_ecommerce_chat_stream(
        request.message,
        adapter=adapter,
        retrieval_limit=max(0, retrieval_limit),
    ):
        if isinstance(event, EcommerceChatRetrievalEvent):
            retrieval_ids = list(event.retrieved_product_ids)
            retrieval_blocks = [block.model_dump() for block in event.blocks]
            if retrieval_ids:
                yield _to_ndjson_line(
                    ThinkingDeltaEvent(
                        traceId=trace_id,
                        delta=(
                            f" matched {len(retrieval_ids)} product(s): "
                            + ", ".join(retrieval_ids)
                        ),
                    )
                )
            else:
                yield _to_ndjson_line(
                    ThinkingDeltaEvent(
                        traceId=trace_id,
                        delta=" no products matched the catalog filter.",
                    )
                )
            yield _to_ndjson_line(ThinkingCompletedEvent(traceId=trace_id))
            thinking_closed = True
            continue

        if isinstance(event, EcommerceChatDeltaEvent):
            if not thinking_closed:
                yield _to_ndjson_line(ThinkingCompletedEvent(traceId=trace_id))
                thinking_closed = True
            if event.text:
                answer_buffer.append(event.text)
                yield _to_ndjson_line(
                    MessageDeltaEvent(traceId=trace_id, delta=event.text)
                )
            continue

        if isinstance(event, EcommerceChatDoneEvent):
            final_provider = event.provider
            final_model = event.model
            final_finish_reason = event.finish_reason
            final_input_tokens = event.input_tokens
            final_output_tokens = event.output_tokens
            continue

    if not thinking_closed:
        yield _to_ndjson_line(ThinkingCompletedEvent(traceId=trace_id))

    assistant_message = MessageModel(
        messageId=_make_message_id("assistant", trace_id),
        conversationId=conversation_id,
        role="assistant",
        content="".join(answer_buffer),
        metadata={
            "router": {
                "intent": "ecommerce.product_consult",
                "module": "ecommerce",
            },
            "generation": {
                "provider": final_provider,
                "model": final_model,
                "finish_reason": final_finish_reason,
                "input_tokens": final_input_tokens,
                "output_tokens": final_output_tokens,
            },
            "retrieval": {
                "source": "ecommerce-catalog-preview",
                "product_ids": retrieval_ids,
            },
            "blocks": retrieval_blocks,
        },
        createdAt=utc_now_iso(),
    )

    yield _to_ndjson_line(
        MessageCompletedEvent(
            traceId=trace_id,
            assistantMessage=assistant_message,
        )
    )
    yield _to_ndjson_line(
        ChatCompletedEvent(
            traceId=trace_id,
            plan=ChatPlanModel(
                useRetrieval=True,
                useTools=False,
                retrievalReason="ecommerce.product_consult (router)",
            ),
            traceStages=[],
        )
    )
