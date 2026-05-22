"""Local-only smoke driver for the ecommerce chat preview endpoint.

Run with:

    OPENAI_API_KEY=...                                     \\
    OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 \\
    PYTHON_LLM_MODEL=qwen-plus                             \\
    PYTHON_LLM_FALLBACK_CHAIN=openai,mock                  \\
    PYTHONPATH=src python scripts/smoke_ecommerce_chat.py

The script never echoes the API key. Use it to confirm an
OpenAI-compatible provider (OpenAI proper / DashScope / vLLM / etc.)
can drive the `/internal/ecommerce/chat` endpoint end-to-end before
shipping or recording a demo.
"""

from __future__ import annotations

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
    response = client.post(
        "/internal/ecommerce/chat",
        json={
            "query": "recommend a laptop under 1500 dollars with at least 16GB RAM",
            "filters": {"category": "laptop", "max_price_usd": 1500, "min_ram_gb": 16},
            "retrieval_limit": 4,
        },
    )
    print(f"smoke> http_status={response.status_code}")
    if response.status_code != 200:
        print(response.text)
        return 1
    body = response.json()
    print(f"smoke> retrieved_ids={body['retrieved_product_ids']}")
    answer = body["answer"]
    print(
        "smoke> answer.meta provider={p} model={m} finish={f} tokens={i}/{o}".format(
            p=answer["provider"],
            m=answer.get("model"),
            f=answer["finish_reason"],
            i=answer.get("input_tokens"),
            o=answer.get("output_tokens"),
        )
    )
    text = answer["text"]
    print("smoke> answer.text >>>")
    print(text if text else "(empty)")
    print("smoke> <<<")
    if answer["provider"] == "mock":
        print("smoke> NOTE: provider resolved to mock (no key or chain misordered).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
