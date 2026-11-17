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

Real sign-in is not wired in yet. Plan: **version 1 signs in with email and password; version 2 moves to Microsoft Entra ID** (`entra_auth.py` is built but not wired in). Until then, set `DEV_AUTH=true` in `.env`, then send `X-User-Id: <app_user id>` on each call. That shortcut has no password, so it must never be on in production. `current_user` in `db.py` is the one function to replace.
Interactive docs at http://localhost:8000/docs.

| Call | What it does |
|---|---|
| `GET /time/week?on=YYYY-MM-DD` | The week's entries, status, per-day minutes, each day's status (`draft`, `submitted`, `approved`, `sent_back`) and the approved minutes |
| `POST /time/entries` | Add an entry (one task or one charge code) |
| `PATCH /time/entries/{id}`, `DELETE /time/entries/{id}` | Change or remove an entry (until the week is approved) |
| `POST /time/weeks/{week_start}/submit` | Submit the week and create the approval for the manager |

## Approvals (WH-30)

| Call | What it does |
|---|---|
| `GET /approvals/inbox` | Pending approvals assigned to you. Each row has who, the week, total minutes, each day's minutes and decision so far, age, due date, overdue flag, level and the timeline (who acted, comment, minutes since the step before). Filters: `subject_type`, `requester_id`, `overdue=true`. Sort: `sort=oldest` (default), `newest`, `due` |
| `POST /approvals/bulk-approve` | Approve many at once (`approval_ids`, up to 100). Ones that can't be approved are skipped with a reason and the rest still go through |
| `POST /approvals/{id}/approve` | Approve the whole week: every day still waiting is approved, and the week becomes `approved` and is locked |
| `POST /approvals/{id}/send-back` | Send the whole week back with a `reason` (and optional `entry_ids` to pin it on): every day still waiting is sent back and the week returns to `draft`. Days already approved stay approved |
| `POST /approvals/{id}/days/{date}/approve` | Approve one day. That day is locked. When every day is decided the approval closes: all approved means the week is approved and locked |
| `POST /approvals/{id}/days/{date}/send-back` | Send one day back with a `reason` (and optional `entry_ids` of that day). The employee fixes it; once every day is decided the week returns to `draft` and the employee resubmits. Only the sent-back days go back to the manager |
| `GET /approvals/{id}/history` | The steps: submitted, delegated, escalated, approved or sent back, with who, when and time taken. Readable by the requester, the current approver and anyone who acted on it |

Only weeks are supported so far. Delegation and escalation come with WH-32.

## Delegation and escalation (WH-32)

| Call | What it does |
|---|---|
| `POST /delegations` | Hand your approvals to someone for a date range (`to_user_id`, `starts_on`, `ends_on`) |
| `GET /delegations` | Delegations you gave and received |
| `DELETE /delegations/{id}` | Remove one you gave (approvals already moved stay with the delegate) |

- New approvals go to the manager's delegate, if one is active. Pending approvals move when a delegation starts.
- A submitted week is due **18:00 IST on the Monday after the week ends** (the next working day if that Monday is a day off or a holiday for the requester). A week submitted after that moment, and every other kind of approval (such as an edit request), is due 2 working days out (`org_settings.approval_due_working_days`), skipping weekends and the requester's location holidays. The other late-submission cases are left for later.
- An approval past its due date moves up to the approver's manager. Notifying people is WH-60, so for now it is recorded in the approval history and audit log.

## Checking Azure's certificate (optional, recommended for production)

`POSTGRES_SSLMODE=require` encrypts the connection. To also check that the server really is Azure, download Microsoft's current root certificate file for Azure Database for PostgreSQL (from their documentation), then set `POSTGRES_SSLMODE=verify-full` and `POSTGRES_SSLROOTCERT=<path to that file>` in `.env`. Everyone who connects to the database does this on their own machine.

## Background worker (WH-07)

```bash
uv run python -m workhub_api.worker   # runs queued jobs; run it next to the API
```

Jobs are rows in the `job` table (`jobs.enqueue(...)`). Failed jobs retry with a growing delay (30 s, 60 s, ... up to 5 tries), and a handler runs inside a savepoint, so a failure undoes its own changes. The worker keeps one repeating job alive, `approval_housekeeping`, every 15 minutes, which applies delegations and escalates overdue approvals.

## Edit requests for locked weeks (WH-22)

An approved week is locked. To change it, file an edit request: a reason and a list of changes. It goes through the same approval engine, so the inbox, delegation, escalation and bulk approve all work for it.

| Call | What it does |
|---|---|
| `POST /time/weeks/{week_start}/edit-requests` | File a request for an **approved** week. Body: `reason` and `changes`, each `{"op":"add", work_date, minutes, task_id or charge_code_id, billable, notes}`, `{"op":"update", entry_id, minutes / billable / notes}` or `{"op":"delete", entry_id}`. One pending request per week |
| `GET /time/edit-requests`, `GET /time/edit-requests/{id}` | Your requests; one request in full (requester, current approver and anyone who acted can read it) |
| `POST /time/edit-requests/{id}/cancel` | Cancel your own pending request |
| `POST /approvals/{id}/approve` | Applies every change in one step. The week stays locked |
| `POST /approvals/{id}/send-back` | Rejects the request (the week is untouched). Needs a `reason`, and no `entry_ids` |

The time rules (no future dates, 24 h a day, one task or charge code, charge codes shared with your team, leave and holiday entries read-only, changes inside that week) are checked when you file it and **again** when it is approved. If they no longer pass at approval, the approval fails with the reason, nothing is applied, and it stays pending.

## HR correction of an approved week

HR can also correct an approved week directly, with a required reason, instead of waiting for an edit request. The changes use the same format and the same time rules as an edit request, are applied at once, and the week stays locked. The audit log records the changes under the HR person's name, with the reason. HR can't correct their own week, and a week with a pending edit request is refused until that is resolved.

| Call | What it does |
|---|---|
| `POST /hr/users/{user_id}/weeks/{week_start}/corrections` | HR role only. Body: `reason` and `changes` (add, update, delete, as for edit requests). Returns the corrected week |

The other HR option, a notification that lets the employee edit the entry, waits for the notification work (WH-60).

## Roles (who can do what)

Roles are employee, manager, hr, finance and admin, and a person can hold several. The API checks them (`permissions.py`); the UI only hides what a role can't open. No sign-in gets 401, a missing role gets 403.

| Action | Needs |
|---|---|
| Log time, submit your week, see your own inbox and delegations | any signed-in user |
| Approve, send back, bulk approve, create a delegation | the **manager** role |
| Be the delegate of a delegation | the **manager** role (checked when the delegation is created) |
| HR, finance and admin only features (leave types, payslips, reports, settings, audit log) | not built yet. Use `Depends(require_roles("hr"))` when you add them |

On top of the role, approvals also check that the approval is **assigned to you** (your report's manager, a delegate, or the escalation target), and you can only touch your own time entries.

## Check before pushing

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
git config core.hooksPath api/.githooks         # one-time: runs lint and types on commit
```

CI (`.github/workflows/api-ci.yml`) runs the same checks against a Postgres service.
