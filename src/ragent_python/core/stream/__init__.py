"""Stream protocol placeholder.

`core/stream/events.py` will absorb the typed SSE/ndjson event union currently
declared in `contracts/public_api.py` (ChatStartedEvent / MessageDeltaEvent /
ToolCallEvent / MessageCompletedEvent / ChatCompletedEvent / ThinkingDelta* /
ChatErrorEvent) plus the future `BlockEmitEvent` for typed renderer blocks.

Step A intentionally keeps this empty: the live protocol still lives in
`contracts/public_api.py` and is consumed by `services/chat_service.py`.
Step D introduces the typed `block.emit` event and pulls the union in here.
"""
