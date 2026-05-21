import { NextResponse } from "next/server";

import { requireAdminApi, requireOrgScopeApi, requireTenantScopeApi, toAuthErrorResponse } from "@/lib/auth/session";
import { getGoIngestionTask } from "@/lib/clients/go-ingestion";
import { ingestionRepository } from "@/lib/repositories/platform-repositories";
import { fetchPython, isPythonBackendEnabled } from "@/lib/server/python-backend";

type RouteContext = {
  params: Promise<{
    taskId: string;
  }>;
};

export async function GET(_request: Request, context: RouteContext) {
  let admin: ReturnType<typeof requireOrgScopeApi> | null = null;
  try {
    admin = requireOrgScopeApi(requireTenantScopeApi(requireAdminApi(_request)));
  } catch (error) {
    return toAuthErrorResponse(error) ?? NextResponse.json({ code: "INTERNAL_ERROR", message: "Unknown error." }, { status: 500 });
  }

  const { taskId } = await context.params;
  if (isPythonBackendEnabled()) {
    const response = await fetchPython(`/internal/ingestion/tasks/${taskId}`);
    const body = await response.json();
    if (!response.ok) {
      const detail = typeof body?.detail === "object" && body.detail ? body.detail : null;
      return NextResponse.json(
        detail ?? {
          code: "INGESTION_TASK_FETCH_FAILED",
          message: "Unable to fetch ingestion task."
        },
        { status: response.status }
      );
    }
    if (body.tenantId !== admin.tenantId || body.orgId !== admin.orgId) {
      return NextResponse.json(
        {
          code: "INGESTION_TASK_NOT_FOUND",
          message: "Ingestion task not found",
          traceId: undefined
        },
        { status: 404 }
      );
    }
    return NextResponse.json(body);
  }
  const localTask = ingestionRepository.getById(taskId, { tenantId: admin.tenantId, orgId: admin.orgId });
  try {
    const goTask = await getGoIngestionTask(taskId);
    if (goTask) {
      ingestionRepository.upsert(goTask);
      const scopedTask = ingestionRepository.getById(taskId, { tenantId: admin.tenantId, orgId: admin.orgId });
      if (scopedTask) {
        return NextResponse.json(scopedTask);
      }
    }
  } catch {}

  if (!localTask) {
    return NextResponse.json(
      {
        code: "INGESTION_TASK_NOT_FOUND",
        message: "Ingestion task not found",
        traceId: undefined
      },
      { status: 404 }
    );
  }

  return NextResponse.json(localTask);
}
