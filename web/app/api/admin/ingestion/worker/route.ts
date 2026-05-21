import { NextResponse } from "next/server";
import { ZodError } from "zod";

import { requireAdminApi, requireOrgScopeApi, requireTenantScopeApi, toAuthErrorResponse } from "@/lib/auth/session";
import { ingestionWorkerRunRequestSchema } from "@/lib/contracts";
import { isPythonBackendEnabled, postPythonJson } from "@/lib/server/python-backend";

export async function POST(request: Request) {
  try {
    requireOrgScopeApi(requireTenantScopeApi(requireAdminApi(request)));

    if (!isPythonBackendEnabled()) {
      return NextResponse.json(
        {
          code: "INGESTION_WORKER_TRIGGER_UNSUPPORTED",
          message: "Worker triggering is only available when the Python ingestion backend is active.",
        },
        { status: 409 }
      );
    }

    const payload = ingestionWorkerRunRequestSchema.parse(await request.json().catch(() => ({})));
    const response = await postPythonJson("/internal/ingestion/worker/run", payload);
    const body = await response.json();
    return NextResponse.json(body, { status: response.status });
  } catch (error) {
    const authError = toAuthErrorResponse(error);
    if (authError) {
      return authError;
    }

    if (error instanceof ZodError) {
      return NextResponse.json(
        {
          code: "INVALID_INGESTION_WORKER_REQUEST",
          message: "Ingestion worker request payload is invalid.",
          issues: error.issues.map((issue) => ({
            path: issue.path.join("."),
            message: issue.message,
          })),
        },
        { status: 400 }
      );
    }

    if (error instanceof Error) {
      console.error("[/api/admin/ingestion/worker][POST]", error.message, error.stack);
      return NextResponse.json(
        {
          code: "INGESTION_WORKER_TRIGGER_FAILED",
          message: error.message,
        },
        { status: 500 }
      );
    }

    const unknownType = Object.prototype.toString.call(error);
    console.error("[/api/admin/ingestion/worker][POST] unknown error", unknownType, error);
    return NextResponse.json(
      {
        code: "INGESTION_WORKER_TRIGGER_UNKNOWN_ERROR",
        message: "Unknown error.",
        errorType: unknownType,
      },
      { status: 500 }
    );
  }
}
