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

## Sample data

```bash
uv run python -m workhub_api.seed   # Jay, Jana, Jim (chain Jim -> Jana -> Jay), 3 teams, 1 project
```

It prints each person's id to use as `X-User-Id`. Safe to run twice (it skips if already there).
It writes to whatever database `.env` points at, so on the shared Azure database run it once.

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
| `GET /approvals/inbox` | Pending approvals assigned to you. Each row has who, the week, total minutes, age, due date, overdue flag, level and the timeline (who acted, comment, minutes since the step before). Filters: `subject_type`, `requester_id`, `overdue=true`. Sort: `sort=oldest` (default), `newest`, `due` |
| `POST /approvals/bulk-approve` | Approve many at once (`approval_ids`, up to 100). Ones that can't be approved are skipped with a reason and the rest still go through |
| `POST /approvals/{id}/approve` | Approve; the week becomes `approved` and is locked |
| `POST /approvals/{id}/send-back` | Send back with a `reason` (and optional `entry_ids` to pin it on); the week returns to `draft` |
| `GET /approvals/{id}/history` | The steps: submitted, delegated, escalated, approved or sent back, with who, when and time taken. Readable by the requester, the current approver and anyone who acted on it |

Only weeks are supported so far. Delegation and escalation come with WH-32.

## Delegation and escalation (WH-32)

| Call | What it does |
|---|---|
| `POST /delegations` | Hand your approvals to someone for a date range (`to_user_id`, `starts_on`, `ends_on`) |
| `GET /delegations` | Delegations you gave and received |
| `DELETE /delegations/{id}` | Remove one you gave (approvals already moved stay with the delegate) |

- New approvals go to the manager's delegate, if one is active. Pending approvals move when a delegation starts.
- Every approval gets a due date, 2 working days out (`org_settings.approval_due_working_days`), skipping weekends and the requester's location holidays.
- An approval past its due date moves up to the approver's manager. Notifying people is WH-60, so for now it is recorded in the approval history and audit log.

## Background worker (WH-07)

```bash
uv run python -m workhub_api.worker   # runs queued jobs; run it next to the API
```

Jobs are rows in the `job` table (`jobs.enqueue(...)`). Failed jobs retry with a growing delay (30 s, 60 s, ... up to 5 tries), and a handler runs inside a savepoint, so a failure undoes its own changes. The worker keeps one repeating job alive, `approval_housekeeping`, every 15 minutes, which applies delegations and escalates overdue approvals.

## Check before pushing

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
git config core.hooksPath api/.githooks         # one-time: runs lint and types on commit
```

CI (`.github/workflows/api-ci.yml`) runs the same checks against a Postgres service.
