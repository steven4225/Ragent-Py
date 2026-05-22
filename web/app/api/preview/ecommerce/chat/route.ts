import { NextResponse } from "next/server";

import {
  isPythonBackendEnabled,
  postPythonJson,
} from "@/lib/server/python-backend";
import type {
  EcommerceChatRequest,
  EcommerceChatResponse,
} from "@/lib/contracts/ecommerce-blocks";

// Preview-only BFF route for the ecommerce chat lane. Forwards to the
// Python `POST /internal/ecommerce/chat` endpoint, which runs the
// catalog filter, builds candidate context, and calls the resolved
// `GenerationAdapter` (real provider if configured, mock otherwise).
// This lane intentionally bypasses `services/chat_service` and the
// main `/api/chat` stream so the platform's generation abstraction can
// be demonstrated end-to-end without touching the production pipeline.

export async function POST(request: Request) {
  if (!isPythonBackendEnabled()) {
    return NextResponse.json(
      {
        code: "PYTHON_BACKEND_DISABLED",
        message: "Set RAG_BACKEND=python to enable the ecommerce chat preview.",
      },
      { status: 503 },
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

  const pythonResponse = await postPythonJson("/internal/ecommerce/chat", forwarded);
  const body = (await pythonResponse.json().catch(() => null)) as EcommerceChatResponse | null;

  if (!pythonResponse.ok || !body) {
    return NextResponse.json(
      {
        code: "ECOMMERCE_CHAT_PREVIEW_FAILED",
        message: "Python preview endpoint returned an error.",
        upstreamStatus: pythonResponse.status,
      },
      { status: 502 },
    );
  }

  return NextResponse.json(body satisfies EcommerceChatResponse);
}
