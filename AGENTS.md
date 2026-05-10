# AGENTS.md

Core instructions for AI coding agents working in this repository.
Detailed runbooks live in `docs/agent/`.

## Project Context

STORM v2 is a Polymarket weather trading bot.

- `scheduler/`: APScheduler jobs, weather fetchers, market selection,
  risk gates, order execution, and resolver.
- `api/`: FastAPI backend.
- `dashboard/`: React/Vite dashboard.
- `db/Init.sql`: Postgres schema and seed data.
- `docker-compose.yml`: local service orchestration.

## Mandatory Safety Rules

- Keep `POLY_DRY_RUN=true` for development and smoke tests.
- Do not place real Polymarket orders unless the user explicitly asks.
- For security-sensitive changes or suspected leaks, follow `SECURITY.md`.
- Never print secrets from `.env`, private keys, Polymarket credentials,
  or full database URLs with credentials.
- Do not drop tables, truncate data, delete Docker volumes, or run
  `docker compose down -v` unless explicitly requested.
- Do not reset git state or discard user edits unless explicitly requested.
- If a command may trade, mutate production-like data, or use financial
  credentials, confirm intent unless it is clearly a dry-run.

## Local Defaults

- The user often runs scheduler locally through `.venv`.
- Scheduler loads `.env` automatically via `scheduler/config.py`.
- Local Postgres may run at `localhost:5432`.
- Docker Compose maps Postgres host `5433` to container `5432`.
- Inside Docker services, database access is `db:5432`; do not change this
  to `5433`.

Preferred smoke-test commands:

```bash
source .venv/bin/activate
python -m scheduler --help
python -m scheduler --list-jobs
POLY_DRY_RUN=true python -m scheduler --once
```

## Workflows

- Scheduler details: `docs/agent/scheduler.md`
- Commit and branch rules: `docs/agent/commit.md`
- Code review workflow: `docs/agent/code-review.md`

When asked to commit, follow `docs/agent/commit.md`.
When asked for review, follow `docs/agent/code-review.md`.
When changing scheduler behavior, follow `docs/agent/scheduler.md`.

## Editing Rules

- Keep scheduler-only work scoped to `scheduler/`, `db/Init.sql`,
  `docker-compose.yml`, `.env.example`, `README.md`, `AGENTS.md`, or
  `docs/agent/` unless the user asks otherwise.
- Do not modify `api/` or `dashboard/` for scheduler-only tasks.
- If changing scheduler DB writes, inspect API services and dashboard types
  before changing column names, statuses, or response shapes.
- If adding a trade status, verify API/dashboard display logic.
- If changing schema or seed data, update `db/Init.sql` and explain migration
  or volume reset impact.

## Verification Baseline

For scheduler-only changes, run when practical:

```bash
python -m compileall scheduler
python -m scheduler --help
python -m scheduler --list-jobs
```

If DB and network access are available:

```bash
POLY_DRY_RUN=true python -m scheduler --once
```

Always report whether verification used `POLY_DRY_RUN=true`.
