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
