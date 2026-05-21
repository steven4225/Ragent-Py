import type { SessionRole } from "@/lib/auth/session";
import { traceRepository } from "@/lib/repositories/platform-repositories";
import { createTraceRunId } from "@/lib/trace/trace";

function readRuntimeEnv(name: string) {
  return process.env?.[name];
}

function normalizeBaseUrl(value: string | undefined) {
  const trimmed = value?.trim();
  if (!trimmed) return "http://127.0.0.1:8000";
  return trimmed.replace(/\/+$/, "");
}

export function isPythonBackendEnabled() {
  return readRuntimeEnv("RAG_BACKEND")?.trim().toLowerCase() === "python";
}

export function getPythonApiBaseUrl() {
  return normalizeBaseUrl(readRuntimeEnv("PYTHON_API_BASE_URL"));
}

export type PythonInternalChatPayload = {
  message: string;
  conversationId?: string;
  userId: string;
  tenantId: string;
  orgId?: string | null;
  role: SessionRole;
};

export type PythonTraceStage = {
  stage: string;
  status: "pending" | "running" | "succeeded" | "failed" | "cancelled";
  metadata?: Record<string, unknown>;
  startedAt?: string | null;
  finishedAt?: string | null;
  durationMs?: number | null;
};

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function appendPythonTraceStages(input: {
  traceId: string;
  conversationId: string | null;
  traceStages: unknown;
  scope: {
    userId: string;
    role: SessionRole;
    tenantId: string | null;
    orgId: string | null;
  };
}) {
  if (!Array.isArray(input.traceStages)) return [];

  return input.traceStages.flatMap((item) => {
    if (!isObjectRecord(item)) return [];
    if (typeof item.stage !== "string") return [];
    if (
      item.status !== "pending" &&
      item.status !== "running" &&
      item.status !== "succeeded" &&
      item.status !== "failed" &&
      item.status !== "cancelled"
    ) {
      return [];
    }

    return [
      traceRepository.append({
        traceId: input.traceId,
        runId: createTraceRunId(input.traceId),
        conversationId: input.conversationId,
        stage: item.stage,
        status: item.status,
        startedAt: typeof item.startedAt === "string" ? item.startedAt : undefined,
        finishedAt: typeof item.finishedAt === "string" ? item.finishedAt : undefined,
        durationMs:
          typeof item.durationMs === "number" && Number.isFinite(item.durationMs) && item.durationMs >= 0
            ? Math.round(item.durationMs)
            : undefined,
        metadata: isObjectRecord(item.metadata) ? item.metadata : {},
        scope: input.scope,
      }),
    ];
  });
}

export async function fetchPython(path: string, init?: RequestInit) {
  return fetch(`${getPythonApiBaseUrl()}${path}`, {
    cache: "no-store",
    ...init,
    headers: {
      Accept: "application/json, application/x-ndjson",
      ...(init?.headers ?? {})
    }
  });
}

export async function postPythonJson(path: string, payload: unknown) {
  return fetchPython(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
