# Ragent-Py

`Ragent-Py` is a **modular Agent platform skeleton**. The Python runtime is
the active execution plane *and* the canonical home for business and
platform modules; the Next.js app under `web/` is the UI / BFF control
plane that sits in front of it.

The skeleton is structured so that each cross-cutting capability
(tools, retrieval sources, ingestion adapters, renderer blocks, intent
patterns, eval suites) is owned by a dedicated sub-registry, and each
business or platform feature ships as a **module** that contributes to
those sub-registries through one `register()` call. The four-layer
split below is enforced in code, not just by convention.

## Architecture

```
src/ragent_python/
├── core/              # orchestration kernel — Module / GenerationAdapter / IntentPattern / streaming contracts
├── infra/             # adapters and registries — registries/, llm/, ingestion/, eval/
├── modules/           # business and platform modules — platform_admin/, demo_corpus/, …
└── ui_contracts/      # renderer block schemas exposed to the BFF
```

### `core/`

The orchestration kernel. Defines what a module *is* (`core/modules`),
the streaming contracts (`core/stream`), the intent-routing primitives
(`core/router`), and the LLM generation interface every module talks to
(`core/generation`). Has **no dependency on `infra/` or `modules/`** —
this is the layer that survives provider / module churn.

### `infra/`

Adapters and registries. The six sub-registries that fan a module's
`register()` output out into globally discoverable artifacts live here
(`infra/registries/`), alongside concrete LLM provider plumbing
(`infra/llm/`), ingestion schema adapters (`infra/ingestion/`), and the
eval registry (`infra/eval/`). `infra/` knows about `core/`'s contracts;
modules import `infra/` registry types but **not** each other.

### `modules/`

Business and platform modules. Each module lives in `modules/<name>/`
and exposes a class satisfying `core.modules.Module`. Its `register()`
returns a `ModuleHookResult` describing what it contributes:

| field                | sub-registry it lands in              |
| -------------------- | ------------------------------------- |
| `tool_pack`          | `ToolPackRegistry`                    |
| `retrieval_sources`  | `RetrievalSourceRegistry`             |
| `ingestion_adapters` | `IngestionSchemaAdapterRegistry`      |
| `renderer_blocks`    | `RendererBlockRegistry`               |
| `intent_patterns`    | `IntentPatternRegistry`               |
| `evals`              | `EvalSuiteRegistry`                   |

Modules **never** import each other; cross-module wiring happens only
through the sub-registries.

### `ui_contracts/`

Pydantic schemas for renderer blocks (product cards, spec-compare
tables, etc.) that the BFF and the React UI consume. This is the single
source of truth for typed UI block payloads; the TS side re-derives its
types from these schemas.

## Bootstrap

`modules.bootstrap_default_modules()` is the single registration
entrypoint. It is idempotent, safe to call across a `clear()` cycle, and
shared by both eager startup (`main.create_app()`) and the legacy MCP
facade's lazy first call.

```python
from ragent_python.modules import bootstrap_default_modules

bootstrap_default_modules()
# registers PlatformAdminModule + DemoCorpusModule against the
# default global registry, then fans their contributions out to the
# six sub-registries above.
```

## Landed Modules

### `modules/platform_admin/`

Platform-level introspection. Owns three tools that previously lived
inline in `mcp/registry.py`:

| tool                  | requires_admin |
| --------------------- | -------------- |
| `list_knowledge_bases` | no             |
| `get_system_setting`  | yes            |
| `get_ingestion_task`  | yes            |

The module contributes a single `ToolPack(name="platform_admin")` to
`ToolPackRegistry`. `mcp/registry.py` is now a thin proxy onto that
registry, so every existing caller (`services/mcp_service`, the
`/internal/mcp/execute` endpoint, the legacy `list_mcp_tools()` /
`get_mcp_tool()` helpers) keeps working unchanged.

### `modules/demo_corpus/`

The six-chunk hand-curated demo dataset (policy / ops / product). Owns:

- `LOCAL_KNOWLEDGE` — the six chunks
- `LocalStaticRetrievalProvider` — the keyword-overlap scorer over them
- one `RetrievalSourceSpec(name="demo_corpus")` published to
  `RetrievalSourceRegistry` via `bootstrap_default_modules()`

The spec's selector activates when the request has no
`knowledgeBaseIds` filter *or* when the request targets at least one of
`kb_policy` / `kb_ops` / `kb_product`. `retrieval/corpus.py` and
`retrieval/providers.py` re-export the moved symbols, so the legacy
hybrid path (`build_default_retrieval_provider` → BM25 + ingestion +
local-static fallback) still works with zero call-site changes.

### `modules/ecommerce/`

First end-to-end business module: an 18-SKU 3C catalog (laptops, phones,
tablets, earbuds, monitors) with structured filters, two renderer
blocks, and a module-scoped chat lane. Contributes to three
sub-registries through `register()`:

| sub-registry              | contribution                                              |
| ------------------------- | --------------------------------------------------------- |
| `RetrievalSourceRegistry` | `ProductCatalogRetrievalProvider` (keyword + filter scorer) |
| `RendererBlockRegistry`   | `ProductCardBlock`, `SpecCompareBlock`                    |
| `IntentPatternRegistry`   | (not yet — reserved for future router work)               |

A dedicated preview surface lives at `web/app/preview/ecommerce/` and
uses four BFF-fronted endpoints that bypass `services/chat_service`
and the main `/api/chat` pipeline by design:

| python endpoint                          | what it does                                                              |
| ---------------------------------------- | ------------------------------------------------------------------------- |
| `POST /internal/ecommerce/search`        | catalog filter + `ProductCardBlock[]`                                     |
| `POST /internal/ecommerce/compare`       | `SpecCompareBlock` side-by-side table for 2–4 selected product ids        |
| `POST /internal/ecommerce/chat`          | retrieval → `GenerationAdapter.generate()` → one-shot `{answer, blocks}`  |
| `POST /internal/ecommerce/chat/stream`   | retrieval → `GenerationAdapter.stream()` → NDJSON `retrieval/delta/done`  |

The streaming wire format is one JSON object per newline. The first
event carries the retrieved product ids + their `ProductCardBlock`s so
the UI can paint the grid before the model starts emitting tokens:

```ndjson
{"type":"retrieval","query":"...","retrieved_product_ids":[...],"blocks":[{"type":"product_card",...}, ...]}
{"type":"delta","text":"The best fit is"}
{"type":"delta","text":" the Lenovo Legion Slim 5"}
{"type":"delta","text":" ..."}
{"type":"done","provider":"openai_compatible","model":"qwen-plus","finish_reason":"stop","input_tokens":null,"output_tokens":null}
```

#### Preview screenshots

`Search` runs `/internal/ecommerce/search`. Empty query lists every
fixture row; `Category` + `Price band` apply structured filters on the
Python side.

![Ecommerce preview · search and filters](docs/img/preview/02-search-filters.png)

`Compare` ticks 2–4 cards then calls `/internal/ecommerce/compare`,
which resolves the product ids on the Python side and returns a
`SpecCompareBlock` with a stable row order (Price / Display / Chip /
Memory / Storage / Battery / Weight / Released).

![Ecommerce preview · spec compare table](docs/img/preview/03-spec-compare.png)

`Ask (stream)` calls `/internal/ecommerce/chat/stream`. The retrieved
product cards land first (off the leading retrieval event), then the
LLM answer streams in delta-by-delta, then provider / model /
finish_reason badges freeze on the final done event. The shot below
is the OpenAI-compatible adapter pointed at DashScope `qwen-plus`:

![Ecommerce preview · streaming chat answer + retrieved cards](docs/img/preview/04-chat-stream.png)

## What the runtime already supports

- streaming chat over `/api/chat/stream`
- non-stream chat over `/api/chat`
- ingestion task creation, tracking, and worker execution
- Qdrant-backed dense retrieval
- BM25 keyword retrieval
- hybrid fusion and reranking
- MCP/tool runtime integration
- trace stage persistence through the BFF
- admin ingestion flows
- verify/e2e scripts for major runtime paths

## Repository Layout

```text
Ragent-Py/
├── .github/workflows/   # CI workflows (pytest)
├── web/                 # Next.js frontend, BFF, admin shell
├── src/ragent_python/
│   ├── core/            # orchestration kernel
│   ├── infra/           # adapters + registries
│   ├── modules/         # platform & business modules
│   ├── ui_contracts/    # renderer block schemas
│   ├── api/             # FastAPI routers
│   ├── services/        # service-layer entry points
│   ├── retrieval/       # retrieval pipeline (hybrid / BM25 / Qdrant / rerank)
│   ├── mcp/             # thin facade over ToolPackRegistry
│   ├── contracts/       # internal & public API pydantic models
│   ├── storage/         # ingestion repository
│   └── worker/          # ingestion worker
├── tests/               # pytest suite
├── scripts/             # verification helpers
└── pyproject.toml
```

## Quick Start

### Option A — One-command Docker Compose (recommended for a demo)

If you only want to **see** the system running, you don't have to
install Python or Node locally — Docker is enough.

```bash
cp .env.docker.example .env.docker     # edit if you want; defaults work
docker compose up                      # builds + starts web + python-api
```

Then open <http://localhost:3000>, log in as the demo user (mock auth
is on by default), and try the chat.

![Ecommerce mode rendered inside the compose stack](docs/img/preview/08-docker-compose-stack.png)

(The screenshot above is the same UI you'd see locally, served by the
`web` container and talking to `python-api` over the compose bridge —
no LLM key was configured; the answer text comes from the mock
generation adapter while the product card grid is rendered from real
ecommerce-module retrieval results.)

What you get out of the box:

* `web` (Next.js BFF) on `:3000`, the same UI you'd run with `npm run dev`.
* `python-api` (FastAPI) on `:8000`, including `/internal/chat/*`,
  `/internal/ecommerce/*`, `/internal/chat/router/*`, and `/healthz`.
* Mock generation adapter — no OpenAI / DashScope / Anthropic key
  needed. Chat answers are deterministic mock responses; the
  ecommerce catalog, retrieval, router, and the streaming protocol
  are real.
* The ingestion sqlite store is persisted in a named volume
  (`ragent_python_data`) so restarts keep state.

Add a vector store (only needed for the qdrant-backed retrieval path):

```bash
docker compose --profile qdrant up
```

That brings up a Qdrant container alongside, and the python-api
container already has `PYTHON_QDRANT_URL=http://qdrant:6333` wired
on the compose bridge network — you only have to flip
`PYTHON_RETRIEVAL_BACKEND` to `hybrid` (or `qdrant`) in `.env.docker`.

Wire a real LLM provider (OpenAI / DashScope / vLLM / …):

Edit `.env.docker`:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PYTHON_LLM_MODEL=qwen-plus
```

The OpenAI-compatible adapter handles all of these uniformly; there is
no vendor-specific code path. Restart with `docker compose up -d` to
apply.

Tear everything down (including the named volumes if you want a fresh
start) with `docker compose down -v`.

| File                       | Role                                                                                  |
| -------------------------- | ------------------------------------------------------------------------------------- |
| `docker-compose.yml`       | Service graph: `python-api`, `web`, optional `qdrant` (profile-gated).                |
| `python/Dockerfile`        | Multi-stage Python 3.12-slim build; runtime image ~170 MB, non-root, `HEALTHCHECK`.   |
| `web/Dockerfile`           | Multi-stage Node 22-alpine build using Next.js `output: "standalone"`; ~220 MB.       |
| `.env.docker.example`      | Annotated template for `.env.docker` (auth mode, LLM provider, retrieval backend).    |
| `.env.docker`              | Your local copy (gitignored).                                                         |

### Option B — Run the services locally (recommended for development)

#### 1. Python backend

```bash
pip install -e ".[dev]"
PYTHONPATH=src uvicorn ragent_python.main:app --host 0.0.0.0 --port 8000
```

`pip install -e ".[dev]"` only pulls `pytest`. LLM provider SDKs are
opt-in extras (`llm-openai`, `llm-anthropic`, `llm-ollama`) and stay
unimported until a provider is wired in.

#### 2. Frontend / BFF

```bash
cd web
npm install
npm run dev
```

#### 3. Local wiring

```bash
RAG_BACKEND=python
PYTHON_API_BASE_URL=http://127.0.0.1:8000
```

With that setup `web/` handles browser-facing routes and Python handles
the execution behind them.

## Platform state persistence

The `web/` BFF stores conversations, messages, traces, ingestion
tasks, knowledge bases, settings, mappings, sample questions, intents,
and users in a single platform-state blob. Three backends are
supported, selected via `TS_PLATFORM_STATE_BACKEND`:

| Backend     | Env value          | Where it stores                                                      | Survives container restart? |
| ----------- | ------------------ | -------------------------------------------------------------------- | --------------------------- |
| JSON file   | `json` (default)   | `TS_PLATFORM_STATE_PATH` (defaults to `.data/ts-platform-state.json`)| Yes, if `.data` is a volume.|
| SQLite      | `sqlite`           | `TS_PLATFORM_STATE_SQLITE_PATH` (defaults to `.data/...sqlite`)      | Yes, if `.data` is a volume.|
| Postgres    | `postgres`         | The connection string in `TS_PLATFORM_STATE_DATABASE_URL`            | Yes, regardless of replica. |

Postgres-specific env vars:

```bash
TS_PLATFORM_STATE_BACKEND=postgres
TS_PLATFORM_STATE_DATABASE_URL=postgres://user:pass@host:5432/dbname
# Optional: override the table name (default platform_state) and row
# key (default "default"). Useful if you want to share a database with
# another app.
TS_PLATFORM_STATE_POSTGRES_TABLE=platform_state
TS_PLATFORM_STATE_POSTGRES_KEY=default
```

The Postgres backend is a write-back JSONB blob with the same
`{state_key TEXT PRIMARY KEY, payload JSONB, updated_at TIMESTAMPTZ}`
shape the SQLite backend uses. Reads come from an in-memory cache that
is hydrated once at boot; writes are applied to the cache
synchronously and flushed to Postgres in the background, coalesced so
that bursts of updates land as one row write. `beforeExit`, `SIGTERM`,
and `SIGINT` all drain the pending flush queue before the process
exits.

This is a deliberately conservative design — the repository layer in
`web/lib/repositories/platform-repositories.ts` is unchanged, so the
Postgres backend is a drop-in replacement for json/sqlite. A proper
per-entity schema (one table per conversation / message / trace etc.)
is a follow-up; the goal of this iteration is "do not lose state when
the container restarts," not "scale to multi-replica".

To verify the adapter end-to-end against a real Postgres:

```bash
docker run -d --rm --name ragent-pg-test \
  -e POSTGRES_PASSWORD=devpass -e POSTGRES_USER=ragent \
  -e POSTGRES_DB=ragent -p 25432:5432 postgres:16-alpine

cd web
DATABASE_URL=postgres://ragent:devpass@127.0.0.1:25432/ragent \
  node --experimental-strip-types ./scripts/verify-postgres-state-backend.mjs
```

## Python Runtime Endpoints

Core runtime (main pipeline):

- `GET /healthz` — also reports the current `generation_provider`
- `POST /internal/chat/turn`
- `POST /internal/chat/stream`
- `POST /internal/retrieval/search`
- `POST /internal/mcp/execute`
- `GET /internal/ingestion/tasks`
- `POST /internal/ingestion/tasks`
- `GET /internal/ingestion/tasks/{taskId}`
- `POST /internal/ingestion/worker/run`

Module preview lanes (bypass `services/chat_service` by design — used
by `web/app/preview/*` only):

- `POST /internal/ecommerce/search`
- `POST /internal/ecommerce/compare`
- `POST /internal/ecommerce/chat`
- `POST /internal/ecommerce/chat/stream` (NDJSON `retrieval` / `delta` / `done` events)

## Ingestion Worker

The ingestion task store supports:

- `PYTHON_INGESTION_BACKEND=sqlite`
- `PYTHON_INGESTION_BACKEND=memory`

Run one worker cycle:

```bash
python -m ragent_python.worker_runner --once
```

Run one worker cycle for a specific task:

```bash
python -m ragent_python.worker_runner --once --task-id ing_123
```

Run a polling worker loop:

```bash
python -m ragent_python.worker_runner
```

## Retrieval and Reranking

Pipeline currently supported:

- Qdrant dense retrieval
- local BM25 keyword retrieval
- reciprocal-rank fusion
- external or heuristic reranking
- module-owned retrieval sources via `RetrievalSourceRegistry`
  (today: `demo_corpus`)

Environment variables:

- `PYTHON_RETRIEVAL_BACKEND`
- `PYTHON_QDRANT_URL`
- `PYTHON_QDRANT_API_KEY`
- `PYTHON_QDRANT_COLLECTION`
- `PYTHON_QDRANT_TIMEOUT_MS`
- `PYTHON_QDRANT_VECTOR_SIZE`
- `PYTHON_RERANKER_BACKEND`
- `PYTHON_RERANKER_TIMEOUT_MS`
- `PYTHON_BGE_RERANKER_URL`
- `PYTHON_RERANK_CANDIDATE_COUNT`
- `PYTHON_RERANK_RETRIEVAL_WEIGHT`
- `PYTHON_RERANK_MODEL_WEIGHT`

Legacy compatibility:

- `BGE_RERANKER_URL` is also accepted

## LLM Generation

`core/generation/adapter.py` defines the `GenerationAdapter` Protocol
that every module must call through. A request carries an input-token
budget (default `16000`) and an output-token budget (default `2000`);
both are configurable via `PYTHON_LLM_MAX_INPUT_TOKENS` /
`PYTHON_LLM_MAX_OUTPUT_TOKENS`.

Provider resolution is chained — `PYTHON_LLM_FALLBACK_CHAIN` defaults to
`openai,anthropic,ollama,mock`. Modules **must not** import provider
SDKs directly; the resolver wires the first reachable provider behind
the adapter.

### OpenAI-compatible adapter

`OpenAICompatibleGenerationAdapter` is the single adapter implementation
used for every OpenAI-compatible provider (OpenAI proper, DashScope,
Moonshot, DeepSeek, SiliconFlow, self-hosted vLLM / SGLang, …). The
adapter does not know the provider's name — it is selected entirely
through environment variables:

| variable                   | purpose                                                  |
| -------------------------- | -------------------------------------------------------- |
| `OPENAI_API_KEY`           | required for any hosted provider (omit for self-hosted)  |
| `OPENAI_BASE_URL`          | provider-specific endpoint base URL                       |
| `PYTHON_LLM_MODEL`         | model name to send on every request                       |
| `PYTHON_LLM_FALLBACK_CHAIN`| resolver chain (`openai` activates the adapter)           |

Example matrices:

| provider          | `OPENAI_BASE_URL`                                          | `PYTHON_LLM_MODEL`      |
| ----------------- | ---------------------------------------------------------- | ----------------------- |
| OpenAI proper     | (unset — SDK default)                                      | `gpt-4o-mini`           |
| DashScope (Qwen)  | `https://dashscope.aliyuncs.com/compatible-mode/v1`        | `qwen-plus`             |
| Self-hosted vLLM  | `http://vllm-host:8000/v1`                                 | `Qwen/Qwen2.5-7B-Instruct` |

Adapter behavior is identical across providers:

- `generate()` returns a one-shot `GenerationResult` with mapped finish
  reason (`length`, `tool_calls` → `tool_call`, `content_filter`).
- `stream()` opens the provider's native streaming endpoint
  (`stream=True`) and yields `GenerationChunk(delta=..., finish_reason=None)`
  per token batch, followed by a final empty chunk with the mapped finish
  reason. `APITimeoutError` / `APIError` collapse to a single chunk
  with `finish_reason="error"` so the module-side orchestrator can still
  close a streaming response cleanly. `MockGenerationAdapter` mimics the
  same shape (word-by-word deltas) so the preview UI keeps streaming
  visibly even with no API key configured.

`.env.example` lists ready-to-paste config blocks for several common
providers.

## Continuous Integration

Two workflows gate `main`:

- `.github/workflows/pytest.yml` — `pytest tests/ -q` on every push to
  `main` and every PR targeting `main`.
- `.github/workflows/web-build.yml` — `npm ci` + `npm run typecheck` +
  `npm run build` against `web/` on the same triggers.

Lint and matrix builds are intentionally out of scope for now.

## Verification

### Python tests

```bash
pytest
```

```bash
python -m compileall src scripts
```

### Python verification scripts

```bash
python scripts/verify_qdrant_e2e.py
python scripts/verify_chat_stream_metadata_e2e.py
python scripts/verify_chat_trace_e2e.py
```

### Frontend / BFF verification

Inside `web/`:

```bash
npm run typecheck
npm run verify:rag-e2e
npm run verify:mcp-runtime-e2e
npm run verify:auth-scope-e2e
# DATABASE_URL=postgres://... npm run verify:postgres-state-backend
```
