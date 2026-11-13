# WorkHub API

FastAPI backend (managed with uv) plus, later, the worker. Postgres is the only datastore.

## Run locally

```bash
cd api
cp .env.example .env                           # edit .env to point at local Docker or Azure Postgres
docker compose up -d db minio                  # skip db if .env points at Azure
uv sync
uv run alembic upgrade head                    # create/update the tables (see docs/erd.md)
uv run uvicorn workhub_api.main:app --reload   # http://localhost:8000/health
```

## Time API (WH-20)

Sign-in is not built yet. Set `DEV_AUTH=true` in `.env`, then send `X-User-Id: <app_user id>` on each call.
Interactive docs at http://localhost:8000/docs.

| Call | What it does |
|---|---|
| `GET /time/week?on=YYYY-MM-DD` | The week's entries, status and per-day minutes |
| `POST /time/entries` | Add an entry (one task or one charge code) |
| `PATCH /time/entries/{id}`, `DELETE /time/entries/{id}` | Change or remove an entry (draft weeks only) |
| `POST /time/weeks/{week_start}/submit` | Submit the week and create the approval for the manager |

## Approvals (WH-30)

| Call | What it does |
|---|---|
| `GET /approvals/inbox` | Pending approvals assigned to you (who, which week, total minutes) |
| `POST /approvals/{id}/approve` | Approve; the week becomes `approved` and is locked |
| `POST /approvals/{id}/send-back` | Send back with a `reason` (and optional `entry_ids` to pin it on); the week returns to `draft` |
| `GET /approvals/{id}/history` | The steps: submitted, approved or sent back, who and when |

Only weeks are supported so far. Delegation and escalation come with WH-32.

## Check before pushing

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
git config core.hooksPath api/.githooks         # one-time: runs lint and types on commit
```

CI (`.github/workflows/api-ci.yml`) runs the same checks against a Postgres service.
