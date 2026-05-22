"""Local-only smoke driver for the streaming ecommerce chat preview.

Run with:

    OPENAI_API_KEY=...                                     \\
    OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 \\
    PYTHON_LLM_MODEL=qwen-plus                             \\
    PYTHON_LLM_FALLBACK_CHAIN=openai,mock                  \\
    PYTHONPATH=src python scripts/smoke_ecommerce_chat_stream.py

Counts the number of delta events observed; a working stream produces
many small deltas instead of one large chunk. The script never echoes
the API key. Use it to verify any OpenAI-compatible provider drives
the new `/internal/ecommerce/chat/stream` endpoint end-to-end.
"""

from __future__ import annotations

import json
import os
import sys

from fastapi.testclient import TestClient

from ragent_python.config import get_settings
from ragent_python.infra.llm.resolver import clear_resolver_cache
from ragent_python.main import create_app


def main() -> int:
    get_settings.cache_clear()
    clear_resolver_cache()
    base_url = os.environ.get("OPENAI_BASE_URL", "(default openai endpoint)")
    model = os.environ.get("PYTHON_LLM_MODEL", "(default)")
    has_key = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    print(f"smoke> base_url={base_url}")
    print(f"smoke> model={model}")
    print(f"smoke> api_key_present={has_key}")

    client = TestClient(create_app())
    with client.stream(
        "POST",
        "/internal/ecommerce/chat/stream",
        json={
            "query": "recommend a laptop under 1500 dollars with at least 16GB RAM",
            "filters": {"category": "laptop", "max_price_usd": 1500, "min_ram_gb": 16},
            "retrieval_limit": 4,
        },
    ) as response:
        print(f"smoke> http_status={response.status_code}")
        print(f"smoke> content_type={response.headers.get('content-type')}")
        if response.status_code != 200:
            print(response.read().decode("utf-8", errors="replace"))
            return 1
        retrieval_count = 0
        delta_count = 0
        done_event: dict | None = None
        accumulated = []
        buffer = ""
        for chunk in response.iter_bytes():
            buffer += chunk.decode("utf-8", errors="replace")
            while True:
                idx = buffer.find("\n")
                if idx < 0:
                    break
                line = buffer[:idx].strip()
                buffer = buffer[idx + 1 :]
                if not line:
                    continue
                event = json.loads(line)
                if event["type"] == "retrieval":
                    retrieval_count += 1
                    print(
                        "smoke> [retrieval] ids={ids} blocks={n}".format(
                            ids=event["retrieved_product_ids"], n=len(event["blocks"])
                        )
                    )
                elif event["type"] == "delta":
                    delta_count += 1
                    accumulated.append(event["text"])
                elif event["type"] == "done":
                    done_event = event
                    print(
                        "smoke> [done] provider={p} model={m} finish={f} tokens={i}/{o}".format(
                            p=event["provider"],
                            m=event.get("model"),
                            f=event["finish_reason"],
                            i=event.get("input_tokens"),
                            o=event.get("output_tokens"),
                        )
                    )
        text = "".join(accumulated)
        print(f"smoke> retrieval_events={retrieval_count} delta_events={delta_count}")
        print("smoke> assembled answer >>>")
        print(text if text else "(empty)")
        print("smoke> <<<")
        if done_event is None:
            print("smoke> WARNING: stream ended without a done event.")
            return 1
        if done_event["provider"] == "mock":
            print("smoke> NOTE: provider resolved to mock (no key or chain misordered).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
