import { NextResponse } from "next/server";

import {
  isPythonBackendEnabled,
  postPythonJson,
} from "@/lib/server/python-backend";
import type {
  EcommerceCompareRequest,
  EcommerceCompareResponse,
} from "@/lib/contracts/ecommerce-blocks";

// Preview-only BFF route for the SpecCompareBlock. Forwards a small
// list of `product_id` values to the Python preview endpoint
// (`POST /internal/ecommerce/compare`) and returns the typed
// `SpecCompareBlock` envelope verbatim. Same shape as the sibling
// `/search` route; deliberately unauthenticated for portfolio-first
// rendering. Chat integration arrives in a later step.

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

  const payload = (await request.json().catch(() => ({}))) as Partial<EcommerceCompareRequest>;
  const ids = Array.isArray(payload.product_ids)
    ? payload.product_ids.filter((value): value is string => typeof value === "string")
    : [];
  const forwarded: EcommerceCompareRequest = { product_ids: ids };

  const pythonResponse = await postPythonJson("/internal/ecommerce/compare", forwarded);
  const body = (await pythonResponse.json().catch(() => null)) as EcommerceCompareResponse | null;

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

  return NextResponse.json(body satisfies EcommerceCompareResponse);
}
