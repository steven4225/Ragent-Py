import {
  isPythonBackendEnabled,
  fetchPython,
} from "@/lib/server/python-backend";
import type { EcommerceChatRequest } from "@/lib/contracts/ecommerce-blocks";

// Preview-only BFF route for the ecommerce streaming chat lane. Pipes
// the NDJSON body from `POST /internal/ecommerce/chat/stream` straight
// through to the browser; the frontend reads it line-by-line via the
// fetch ReadableStream. Bypasses `services/chat_service` and the main
// `/api/chat` stream protocol by design.

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  if (!isPythonBackendEnabled()) {
    return new Response(
      JSON.stringify({
        code: "PYTHON_BACKEND_DISABLED",
        message: "Set RAG_BACKEND=python to enable the ecommerce chat stream preview.",
      }),
      { status: 503, headers: { "Content-Type": "application/json" } },
    );
  }

  const payload = (await request.json().catch(() => ({}))) as Partial<EcommerceChatRequest>;
  const forwarded: EcommerceChatRequest = {
    query: typeof payload.query === "string" ? payload.query : "",
    filters: payload.filters ?? {},
    retrieval_limit:
      typeof payload.retrieval_limit === "number" && payload.retrieval_limit > 0
        ? payload.retrieval_limit
        : 5,
  };

  const upstream = await fetchPython("/internal/ecommerce/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(forwarded),
  });

  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text().catch(() => "");
    return new Response(
      JSON.stringify({
        code: "ECOMMERCE_CHAT_STREAM_FAILED",
        message: "Python preview stream endpoint returned an error.",
        upstreamStatus: upstream.status,
        detail: text.slice(0, 512),
      }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "application/x-ndjson",
      "Cache-Control": "no-store",
      "X-Accel-Buffering": "no",
    },
  });
}
