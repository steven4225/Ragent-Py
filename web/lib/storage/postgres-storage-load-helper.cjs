// Subprocess helper used by PostgresStorageAdapter to load the
// initial state blob synchronously from the main process's
// perspective. The main process pipes a small JSON payload over
// stdin describing the connection + key, and this helper queries
// Postgres, prints the result to stdout, and exits.
//
// Output is a single JSON line: {"found": true, "payload": <state>}
// or {"found": false}. Errors are written to stderr with a non-zero
// exit code so execFileSync raises.
//
// CommonJS so we can be invoked directly via `node <path>` from any
// runtime configuration without worrying about ESM resolution.

const path = require("node:path");
const fs = require("node:fs");

function findPgFromHere(start) {
  let dir = start;
  while (true) {
    const candidate = path.join(dir, "node_modules", "pg");
    if (fs.existsSync(candidate)) return require(candidate);
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return require("pg");
}

async function main() {
  let raw = "";
  for await (const chunk of process.stdin) {
    raw += typeof chunk === "string" ? chunk : chunk.toString("utf8");
  }
  if (!raw.trim()) {
    process.stdout.write(JSON.stringify({ found: false }));
    return;
  }

  const { databaseUrl, tableName, stateKey } = JSON.parse(raw);
  if (!databaseUrl || !tableName || !stateKey) {
    throw new Error("postgres-storage-load-helper: missing required fields");
  }

  const pg = findPgFromHere(__dirname);
  const client = new pg.Client({ connectionString: databaseUrl });
  await client.connect();
  try {
    await client.query(
      `
        CREATE TABLE IF NOT EXISTS ${tableName} (
          state_key TEXT PRIMARY KEY,
          payload JSONB NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `
    );
    const row = await client.query(
      `SELECT payload FROM ${tableName} WHERE state_key = $1`,
      [stateKey]
    );
    if (row.rowCount && row.rowCount > 0) {
      process.stdout.write(
        JSON.stringify({ found: true, payload: row.rows[0].payload })
      );
    } else {
      process.stdout.write(JSON.stringify({ found: false }));
    }
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  process.stderr.write(
    `postgres-storage-load-helper failed: ${
      error && error.stack ? error.stack : error
    }\n`
  );
  process.exit(1);
});
