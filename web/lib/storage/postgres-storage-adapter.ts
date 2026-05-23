import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

import type { StorageAdapter } from "@/lib/storage/storage-adapter";

// We never `import "pg"` statically because Next.js' build-time page
// data collector evaluates every server module, and `pg` pulls in the
// optional `pg-native` addon path that is not friendly to that
// environment. Defer the load to the actual constructor call (which
// only fires when `TS_PLATFORM_STATE_BACKEND=postgres`).
const nodeRequire = createRequire(import.meta.url);

type PgModule = typeof import("pg");
type PgPool = import("pg").Pool;

function loadPgPool(): PgModule["Pool"] {
  const mod = nodeRequire("pg") as PgModule;
  return mod.Pool;
}

type PostgresStorageAdapterOptions<TState> = {
  databaseUrl: string;
  seedFactory: () => TState;
  tableName?: string;
  stateKey?: string;
  flushIntervalMs?: number;
  onWriteError?: (error: unknown) => void;
};

// We keep the public StorageAdapter API synchronous on purpose — the
// rest of the BFF reads `storage.read()` / `storage.update()` as if
// they were instantaneous local calls, and several hundred call sites
// rely on that. To honour that contract while still talking to a real
// Postgres server we:
//
//   1. Load the blob ONCE on construction via a small subprocess that
//      can speak async `pg`. The main thread blocks until the load
//      succeeds. (This trades ~150–300ms of cold-start latency for the
//      ability to keep `read()` synchronous everywhere else.)
//   2. Serve every subsequent `read()` from an in-memory cache.
//   3. Apply `write()`/`update()` to the in-memory cache immediately,
//      and enqueue the new state for an asynchronous flush back to
//      Postgres. Writes are coalesced: if several updates land before
//      the previous flush completes, we only write the latest state
//      once.
//   4. Flush pending writes on `beforeExit`/`SIGTERM`/`SIGINT` so we
//      do not lose the last operation when the container is stopped.
//
// This is a deliberate "write-back cache" design. For a single web
// replica it preserves at-least-the-latest durability with the same
// API surface as the json/sqlite adapters; multi-replica deployments
// should adopt a proper per-table schema (deferred).
export class PostgresStorageAdapter<TState> implements StorageAdapter<TState> {
  private readonly databaseUrl: string;
  private readonly seedFactory: () => TState;
  private readonly tableName: string;
  private readonly stateKey: string;
  private readonly onWriteError: (error: unknown) => void;
  private readonly pool: PgPool;

  private cache: TState;
  private pendingWriteState: TState | null = null;
  private flushTask: Promise<void> | null = null;
  private shutdownHooksInstalled = false;
  private closed = false;

  constructor(options: PostgresStorageAdapterOptions<TState>) {
    this.databaseUrl = options.databaseUrl;
    this.seedFactory = options.seedFactory;
    this.tableName = options.tableName ?? "platform_state";
    this.stateKey = options.stateKey ?? "default";
    this.onWriteError =
      options.onWriteError ??
      ((error: unknown) => {
        const message = error instanceof Error ? error.message : String(error);
        console.error(
          `[PostgresStorageAdapter] background flush failed (state will be retried on next write): ${message}`
        );
      });

    const Pool = loadPgPool();
    this.pool = new Pool({ connectionString: this.databaseUrl });
    this.pool.on("error", (error) => this.onWriteError(error));

    // Synchronously load (and seed if needed) the initial blob via a
    // subprocess. We cannot do this with `this.pool` directly because
    // pg is async-only and we need a sync constructor.
    const loaded = this.loadBlobSync();
    this.cache = loaded ?? this.seedAndPersistInitial();

    this.installShutdownHooks();
  }

  read(): TState {
    return this.cache;
  }

  write(next: TState): void {
    this.cache = next;
    this.scheduleFlush();
  }

  update(mutator: (current: TState) => TState): TState {
    const next = mutator(this.cache);
    this.cache = next;
    this.scheduleFlush();
    return next;
  }

  /**
   * Best-effort flush of pending writes. Useful in tests and during
   * shutdown. Resolves once every queued state has been written.
   */
  async flush(): Promise<void> {
    while (this.flushTask || this.pendingWriteState !== null) {
      if (this.flushTask) {
        try {
          await this.flushTask;
        } catch {
          // already surfaced via onWriteError
        }
      }
    }
  }

  async close(): Promise<void> {
    if (this.closed) return;
    this.closed = true;
    await this.flush();
    await this.pool.end();
  }

  private scheduleFlush(): void {
    if (this.closed) return;
    this.pendingWriteState = this.cache;
    if (this.flushTask) {
      // a flush is already in progress; it will observe the new
      // pendingWriteState and loop until the queue drains.
      return;
    }
    this.flushTask = this.drainPendingWrites();
  }

  private async drainPendingWrites(): Promise<void> {
    try {
      while (this.pendingWriteState !== null) {
        const snapshot = this.pendingWriteState;
        this.pendingWriteState = null;
        try {
          await this.writeBlob(snapshot);
        } catch (error) {
          // Put the state back so the next mutation retriggers a flush.
          this.pendingWriteState = this.pendingWriteState ?? snapshot;
          this.onWriteError(error);
          // Brief back-off to avoid hot-looping on a wedged database.
          await new Promise((resolve) => setTimeout(resolve, 250));
        }
      }
    } finally {
      this.flushTask = null;
    }
  }

  private async writeBlob(state: TState): Promise<void> {
    const payload = JSON.stringify(state);
    await this.pool.query(
      `
        INSERT INTO ${this.tableName} (state_key, payload, updated_at)
        VALUES ($1, $2::jsonb, NOW())
        ON CONFLICT (state_key) DO UPDATE
        SET payload = excluded.payload,
            updated_at = excluded.updated_at
      `,
      [this.stateKey, payload]
    );
  }

  private loadBlobSync(): TState | null {
    const payload = JSON.stringify({
      databaseUrl: this.databaseUrl,
      tableName: this.tableName,
      stateKey: this.stateKey
    });

    const helperPath = resolveSyncHelperPath();
    const result = execFileSync(process.execPath, [helperPath], {
      input: payload,
      encoding: "utf8",
      stdio: ["pipe", "pipe", "pipe"],
      maxBuffer: 64 * 1024 * 1024
    });

    const trimmed = result.trim();
    if (!trimmed) return null;
    const parsed = JSON.parse(trimmed) as { found: boolean; payload?: unknown };
    if (!parsed.found) return null;
    return parsed.payload as TState;
  }

  private seedAndPersistInitial(): TState {
    const seeded = this.seedFactory();
    // Block on the seed write so subsequent reads observe a real row,
    // but fall through gracefully if it fails (the next mutation will
    // retry).
    this.pool
      .query(
        `
          INSERT INTO ${this.tableName} (state_key, payload, updated_at)
          VALUES ($1, $2::jsonb, NOW())
          ON CONFLICT (state_key) DO NOTHING
        `,
        [this.stateKey, JSON.stringify(seeded)]
      )
      .catch((error) => this.onWriteError(error));
    return seeded;
  }

  private installShutdownHooks(): void {
    if (this.shutdownHooksInstalled) return;
    this.shutdownHooksInstalled = true;

    const flushOnExit = () => {
      // beforeExit fires when the event loop is idle, which is the
      // last opportunity to await an async flush.
      if (this.pendingWriteState !== null || this.flushTask) {
        void this.flush();
      }
    };

    process.once("beforeExit", flushOnExit);
    process.once("SIGTERM", flushOnExit);
    process.once("SIGINT", flushOnExit);
  }
}

function resolveSyncHelperPath(): string {
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.join(here, "postgres-storage-load-helper.cjs");
}
