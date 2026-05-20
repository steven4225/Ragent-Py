# Python Migration Workspace

This directory is the target workspace for the Python refactor of Ragent.

Initial documents:

- `MIGRATION_PLAN.md`
- `MIGRATION_CONSTRAINTS.md`

The implementation should follow these documents unless later decisions explicitly supersede them.

## Local Run

After installing dependencies from `pyproject.toml`, run the app with:

```bash
uvicorn ragent_python.main:app --host 0.0.0.0 --port 8000
```

If using the `src/` layout directly, ensure `PYTHONPATH=src`.

## Current Phase-1 Endpoints

- `GET /healthz`
- `POST /internal/chat/turn`
- `POST /internal/chat/stream`
- `POST /internal/retrieval/search`
- `POST /internal/mcp/execute`
- `GET /internal/ingestion/tasks`
- `POST /internal/ingestion/tasks`
- `GET /internal/ingestion/tasks/{taskId}`

## Ingestion Worker

The ingestion task store is configurable:

- `PYTHON_INGESTION_BACKEND=sqlite` for cross-process task sharing
- `PYTHON_INGESTION_BACKEND=memory` for isolated local/testing flows

Run one worker cycle manually:

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

## Retrieval Backends

Python retrieval now supports a provider chain with Qdrant-first lookup when configured.

- `PYTHON_RETRIEVAL_BACKEND=hybrid` keeps Qdrant as the preferred backend and preserves local fallbacks
- `PYTHON_RETRIEVAL_BACKEND=qdrant` enables Qdrant-first retrieval
- `PYTHON_RETRIEVAL_BACKEND=local` keeps only the local fallback providers

Relevant environment variables:

- `PYTHON_QDRANT_URL`
- `PYTHON_QDRANT_API_KEY`
- `PYTHON_QDRANT_COLLECTION`
- `PYTHON_QDRANT_TIMEOUT_MS`
- `PYTHON_QDRANT_VECTOR_SIZE`

When `executionPlan.indexing.storeType=qdrant`, the ingestion worker writes chunk payloads into Qdrant during the indexing stage.

To replay the full ingestion -> worker -> Qdrant -> `/api/chat` validation against running local services:

```bash
python scripts/verify_qdrant_e2e.py
```

Optional environment overrides:

- `RAGENT_WEB_BASE_URL`
- `RAGENT_QDRANT_URL`
- `RAGENT_QDRANT_COLLECTION`
- `RAGENT_TENANT_ID`
- `RAGENT_ORG_ID`
