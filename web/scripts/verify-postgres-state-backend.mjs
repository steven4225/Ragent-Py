#!/usr/bin/env node
// Manual smoke test for the PostgresStorageAdapter.
//
// What it exercises:
//   * Cold start seeds the row when the table is empty.
//   * Synchronous read()/update()/write() against the in-memory cache.
//   * Async write-through flush actually lands in Postgres.
//   * Coalesced writes: multiple mutations land as a single latest
//     state (the adapter is allowed to skip intermediate snapshots).
//   * Warm start: a second adapter instance observes the writes the
//     first instance produced (proves durability).
//
// How to run:
//   1. Start a disposable Postgres locally, for example:
//        docker run -d --name ragent-pg-test \
//          -e POSTGRES_PASSWORD=devpass -e POSTGRES_USER=ragent \
//          -e POSTGRES_DB=ragent -p 25432:5432 postgres:16-alpine
//   2. From `web/`:
//        DATABASE_URL=postgres://ragent:devpass@127.0.0.1:25432/ragent \
//        node --experimental-strip-types ./scripts/verify-postgres-state-backend.mjs
//
// The script exits non-zero on the first failed assertion. The table
// used for the run is name-spaced with `Date.now()` so concurrent
// invocations do not collide.

import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const adapterPath = path.join(here, "..", "lib", "storage", "postgres-storage-adapter.ts");

const { PostgresStorageAdapter } = await import(adapterPath);

const databaseUrl =
  process.env.DATABASE_URL?.trim() ||
  process.env.TS_PLATFORM_STATE_DATABASE_URL?.trim() ||
  "";

if (!databaseUrl) {
  console.error(
    "DATABASE_URL is required. Example: " +
      "DATABASE_URL=postgres://ragent:devpass@127.0.0.1:25432/ragent " +
      "node --experimental-strip-types ./scripts/verify-postgres-state-backend.mjs"
  );
  process.exit(2);
}

const tableName = `platform_state_smoke_${Date.now()}`;

function seedFactory() {
  return {
    conversations: [{ conversationId: "conv_seed", title: "Seeded conversation" }],
    messages: []
  };
}

function assertEqual(actual, expected, label) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) {
    throw new Error(`assertion failed [${label}]:\n  expected: ${e}\n  actual:   ${a}`);
  }
}

async function main() {
  // ---- cold start ----
  console.log("[1/5] cold start: constructing adapter against empty table");
  const adapter = new PostgresStorageAdapter({
    databaseUrl,
    seedFactory,
    tableName
  });
  const initial = adapter.read();
  assertEqual(initial.conversations, seedFactory().conversations, "seeded conversations");

  // ---- synchronous mutations ----
  console.log("[2/5] mutations: append message + rename conversation (coalesced)");
  adapter.update((state) => ({
    ...state,
    messages: [
      ...state.messages,
      { messageId: "msg_1", conversationId: "conv_seed", role: "user", content: "hello" }
    ]
  }));
  adapter.update((state) => ({
    ...state,
    conversations: state.conversations.map((conv) =>
      conv.conversationId === "conv_seed" ? { ...conv, title: "Renamed" } : conv
    )
  }));
  // read should immediately reflect both updates (in-memory cache).
  const afterMutations = adapter.read();
  assertEqual(afterMutations.messages[0].content, "hello", "in-memory message content");
  assertEqual(afterMutations.conversations[0].title, "Renamed", "in-memory title update");

  // ---- explicit flush ----
  console.log("[3/5] flush: waiting for background writer to settle");
  await adapter.flush();
  await adapter.close();

  // ---- warm start ----
  console.log("[4/5] warm start: second adapter must observe persisted state");
  const second = new PostgresStorageAdapter({
    databaseUrl,
    seedFactory,
    tableName
  });
  const loaded = second.read();
  assertEqual(loaded.messages[0].content, "hello", "persisted message after restart");
  assertEqual(loaded.conversations[0].title, "Renamed", "persisted title after restart");
  await second.close();

  // ---- cleanup ----
  console.log("[5/5] cleanup: dropping smoke table");
  const { default: pkg } = await import("pg");
  const client = new pkg.Client({ connectionString: databaseUrl });
  await client.connect();
  try {
    await client.query(`DROP TABLE IF EXISTS ${tableName}`);
  } finally {
    await client.end();
  }

  console.log("\nPostgresStorageAdapter smoke: PASS");
}

main().catch((error) => {
  console.error("\nPostgresStorageAdapter smoke: FAIL");
  console.error(error);
  process.exit(1);
});
