# AGENTS.md

## Purpose

This directory contains the new Python backend project for the Ragent refactor.

Agents working here must treat this as a staged migration project, not a greenfield rewrite.

## Required Reading

Before making changes, always read and follow:

- `MIGRATION_PLAN.md`
- `MIGRATION_CONSTRAINTS.md`
- `MIGRATION_DECISIONS.md`
- `MIGRATION_MAPPING.md`
- `MIGRATION_CHECKLIST.md`
- `MIGRATION_COMPAT_MATRIX.md`

If there is any conflict, use this priority:

1. `MIGRATION_CONSTRAINTS.md`
2. `MIGRATION_DECISIONS.md`
3. `MIGRATION_COMPAT_MATRIX.md`
4. `MIGRATION_PLAN.md`
5. `MIGRATION_MAPPING.md`
6. `MIGRATION_CHECKLIST.md`

## Core Rules

1. This is a migration project, not a product redesign.
2. Preserve external behavior where the frontend, admin shell, and verification flows depend on it.
3. Re-implement internals in Python-native architecture.
4. Do not port Go line-by-line.
5. Do not rewrite the frontend.
6. Do not remove old TS/Go implementations until Python is stable and validated.
7. Keep the ability to switch between old and new backends during migration.

## Scope Rules

### Keep in place

The following remain in the existing TypeScript/Next.js shell during phase 1:

- frontend pages
- frontend components
- auth/session/OIDC behavior
- tenant/org/admin scope shell
- public API shell in `web/app/api/*`

### Python owns

The Python backend is the target runtime for:

- chat
- retrieval
- ingestion
- MCP runtime

## Compatibility Rules

### Public API

Do not break compatibility for:

- `/api/chat`
- `/api/chat/stream`
- `/api/conversations`
- `/api/messages`
- `/api/trace`
- `/api/admin/*`

### Stream protocol

Preserve NDJSON stream event compatibility, including:

- `chat.started`
- `tool.call`
- `message.delta`
- `message.completed`
- `chat.completed`
- `thinking.delta`
- `thinking.completed`
- `chat.error`

Preserve `tool.call.status` lifecycle:

- `queued`
- `running`
- `succeeded`
- `failed`

### Trace and metadata

Preserve:

- `traceId` propagation
- assistant metadata needed by UI/tests
- retrieval metadata needed by UI/tests
- ingestion task observability
- tool-call observability

## Ingestion Rules

Do not use FastAPI `BackgroundTasks` as the final ingestion execution model.

Target model must be:

- API
- worker
- DB-backed task lifecycle

## Change Control Rules

1. Make the smallest necessary change for the current task.
2. Do not refactor unrelated code.
3. Do not clean up unrelated files.
4. Do not expand scope unless it is required for:
   - compatibility
   - current-task unblock
5. If something can wait until a later phase, record it and move on.

## Git Rules

1. Work only in:
   - `python/`
   - explicitly required BFF integration files
2. Do not modify unrelated files.
3. Never commit:
   - `MIGRATION_*.md`
   - `.env`
   - private notes
   - local cache files
4. Never run destructive Git operations:
   - `git reset --hard`
   - `git checkout --`
   - history rewrites
   - amend of prior commits unless explicitly requested
5. Unless explicitly asked, do not commit automatically.

### Commit style

Use focused single-purpose commits, for example:

- `feat(python): scaffold fastapi app and health check`
- `feat(chat): add internal chat turn endpoint`
- `feat(stream): add ndjson chat stream`
- `feat(retrieval): add python retrieval skeleton`
- `feat(ingestion): add task api and worker skeleton`
- `chore(bff): add python backend switch`
- `fix(contract): preserve chat response compatibility`

## Execution Style

Default behavior:

- do the work directly
- avoid long planning prose
- avoid unnecessary back-and-forth
- only pause when:
  - compatibility requirements conflict
  - destructive deletion is required
  - there are multiple materially different architecture choices
  - migration documents are inconsistent

## Progress Reporting

After each work chunk, report briefly:

- what changed
- why it changed
- what the next step is

## Validation Rules

At each stage, validate the current scope with concrete checks.

Prefer reuse of existing verification expectations from `web/scripts/verify-*.mjs`.

Minimum expectations:

- routes start
- response shapes remain compatible
- stream event format remains compatible
- fallback path remains possible until migration is stable

## Current Preferred Order

1. Python project skeleton
2. `GET /healthz`
3. `POST /internal/chat/turn`
4. `POST /internal/chat/stream`
5. BFF backend switch for chat
6. retrieval
7. MCP runtime
8. ingestion
9. cleanup only after validation
