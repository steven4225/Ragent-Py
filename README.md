# Ragent-Py

`Ragent-Py` is a full-stack Agent platform skeleton built with:

- `Next.js + React + TypeScript` for the UI, BFF, and control plane
- `Python + FastAPI` for the AI execution plane

The project is designed around a split architecture:

- the `web/` app owns the user-facing product shell, auth-facing API routes, admin views, and trace read models
- the Python runtime owns chat execution, retrieval, ingestion, worker flows, reranking, and tool runtime behavior

This repository is meant to be a **real project base**, not a toy RAG demo. It already includes retrieval, ingestion, workers, MCP-style tool execution, streaming chat, and end-to-end verification entry points.

## What It Already Supports

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

## Architecture

### `web/`

The Next.js app is the active frontend and control plane.

Responsibilities:

- chat UI
- admin UI
- BFF routes under `/api/*`
- auth / scope enforcement
- trace read models
- browser-facing contracts and stream handling

### `src/ragent_python/`

The Python runtime is the active execution plane.

Responsibilities:

- chat turn execution
- chat stream event generation
- retrieval orchestration
- ingestion task lifecycle
- worker runtime
- reranker integration
- MCP/tool execution

## Repository Layout

```text
python/
  web/                    # Next.js frontend, BFF, admin shell
  src/ragent_python/      # Python runtime
  tests/                  # Python tests
  scripts/                # Python verification helpers
  pyproject.toml          # Python package config
```

## Quick Start

### 1. Python backend

Install Python dependencies:

```bash
pip install -e .[dev]
```

Run the backend:

```bash
uvicorn ragent_python.main:app --host 0.0.0.0 --port 8000
```

If needed, set:

```bash
PYTHONPATH=src
```

### 2. Frontend / BFF

Install frontend dependencies:

```bash
cd web
npm install
```

Run the web app:

```bash
npm run dev
```

### 3. Basic local wiring

Typical local development uses:

```bash
RAG_BACKEND=python
PYTHON_API_BASE_URL=http://127.0.0.1:8000
```

With that setup:

- `web/` handles the browser-facing routes
- Python handles the execution behind them

## Python Runtime Endpoints

Current internal execution endpoints include:

- `GET /healthz`
- `POST /internal/chat/turn`
- `POST /internal/chat/stream`
- `POST /internal/retrieval/search`
- `POST /internal/mcp/execute`
- `GET /internal/ingestion/tasks`
- `POST /internal/ingestion/tasks`
- `GET /internal/ingestion/tasks/{taskId}`
- `POST /internal/ingestion/worker/run`

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

The runtime currently supports:

- Qdrant dense retrieval
- local BM25 keyword retrieval
- reciprocal-rank fusion
- external or heuristic reranking

Important environment variables:

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

## Verification

### Python

Run tests:

```bash
pytest
```

Run bytecode compile verification:

```bash
python -m compileall src scripts
```

### Python verification scripts

Verify ingestion -> worker -> Qdrant -> `/api/chat`:

```bash
python scripts/verify_qdrant_e2e.py
```

Verify `/api/chat/stream` metadata:

```bash
python scripts/verify_chat_stream_metadata_e2e.py
```

Verify trace stage persistence through the BFF:

```bash
python scripts/verify_chat_trace_e2e.py
```

### Frontend / BFF verification

Inside `web/`:

```bash
npm run typecheck
npm run verify:rag-e2e
npm run verify:mcp-runtime-e2e
npm run verify:auth-scope-e2e
```
