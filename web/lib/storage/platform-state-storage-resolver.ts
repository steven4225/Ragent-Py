import path from "node:path";

import { PostgresStorageAdapter } from "@/lib/storage/postgres-storage-adapter";
import { SqliteStorageAdapter } from "@/lib/storage/sqlite-storage-adapter";
import type { StorageAdapter } from "@/lib/storage/storage-adapter";
import { TsLocalStorageAdapter } from "@/lib/storage/ts-local-storage-adapter";

type SupportedBackend = "sqlite" | "json" | "postgres";

type ResolveStorageOptions<TState> = {
  seedFactory: () => TState;
};

function parseBackend(value: string | undefined): SupportedBackend {
  const normalized = value?.trim().toLowerCase();
  if (normalized === "sqlite") return "sqlite";
  if (normalized === "postgres" || normalized === "pg") return "postgres";
  return "json";
}

function resolveDatabaseUrl(): string {
  const fromEnv = process.env.TS_PLATFORM_STATE_DATABASE_URL?.trim() || process.env.DATABASE_URL?.trim();
  if (!fromEnv) {
    throw new Error(
      "TS_PLATFORM_STATE_BACKEND=postgres but neither TS_PLATFORM_STATE_DATABASE_URL nor DATABASE_URL is set. " +
        "Provide a connection string like postgres://user:pass@host:5432/dbname."
    );
  }
  return fromEnv;
}

export function resolvePlatformStateStorage<TState>(options: ResolveStorageOptions<TState>): {
  backend: SupportedBackend;
  storage: StorageAdapter<TState>;
} {
  const backend = parseBackend(process.env.TS_PLATFORM_STATE_BACKEND);

  if (backend === "postgres") {
    return {
      backend,
      storage: new PostgresStorageAdapter<TState>({
        databaseUrl: resolveDatabaseUrl(),
        tableName: process.env.TS_PLATFORM_STATE_POSTGRES_TABLE?.trim() || "platform_state",
        stateKey: process.env.TS_PLATFORM_STATE_POSTGRES_KEY?.trim() || "default",
        seedFactory: options.seedFactory
      })
    };
  }

  if (backend === "sqlite") {
    const sqlitePath =
      process.env.TS_PLATFORM_STATE_SQLITE_PATH?.trim() || path.join(process.cwd(), ".data", "ts-platform-state.sqlite");
    return {
      backend,
      storage: new SqliteStorageAdapter<TState>({
        filePath: sqlitePath,
        seedFactory: options.seedFactory
      })
    };
  }

  const jsonPath =
    process.env.TS_PLATFORM_STATE_PATH?.trim() || path.join(process.cwd(), ".data", "ts-platform-state.json");
  return {
    backend,
    storage: new TsLocalStorageAdapter<TState>({
      filePath: jsonPath,
      seedFactory: options.seedFactory
    })
  };
}
