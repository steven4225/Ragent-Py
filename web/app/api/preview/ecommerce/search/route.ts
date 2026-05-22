import { NextResponse } from "next/server";

import {
  isPythonBackendEnabled,
  postPythonJson,
} from "@/lib/server/python-backend";
import type {
  EcommerceSearchRequest,
  EcommerceSearchResponse,
} from "@/lib/contracts/ecommerce-blocks";

// Preview-only BFF route. The ecommerce module is the first business
// module on the platform; this route forwards the search payload to the
// Python preview endpoint (`POST /internal/ecommerce/search`) and
// returns the typed `ProductCardBlock` list verbatim. Intentionally
// unauthenticated: portfolio-first goal is to render the block in the
// browser without an auth ceremony. Production gating lands when chat
// integration arrives in a later step.

export async function POST(request: Request) {
  if (!isPythonBackendEnabled()) {
    return NextResponse.json(
      {
        code: "PYTHON_BACKEND_DISABLED",
        message: "Set RAG_BACKEND=python to enable the ecommerce preview.",
      },
      { status: 503 },
    );
  }

  const payload = (await request.json().catch(() => ({}))) as Partial<EcommerceSearchRequest>;
  const forwarded: EcommerceSearchRequest = {
    query: typeof payload.query === "string" ? payload.query : "",
    filters: payload.filters ?? {},
    limit: typeof payload.limit === "number" && payload.limit > 0 ? payload.limit : 6,
  };

  const pythonResponse = await postPythonJson("/internal/ecommerce/search", forwarded);
  const body = (await pythonResponse.json().catch(() => null)) as EcommerceSearchResponse | null;

  if (!pythonResponse.ok || !body) {
    return NextResponse.json(
      {
        code: "ECOMMERCE_PREVIEW_FAILED",
        message: "Python preview endpoint returned an error.",
        upstreamStatus: pythonResponse.status,
      },
      { status: 502 },
    );
  }

  return NextResponse.json(body satisfies EcommerceSearchResponse);
}
