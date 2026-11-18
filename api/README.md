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

It also gives everyone without a password the dev password `workhub-dev-1` (sign in as `jim@example.com`, `jana@example.com` or `jay@example.com`) and adds four sample leave types (Earned, Casual, Sick, LWP) with a "Leave" charge code. The leave numbers are placeholders; HR sets the real policy with `POST /leave/types`.
Safe to run twice: each part skips what is already there. It writes to whatever database `.env` points at.

## Sign-in (WH-04, version 1: email and password)

Version 2 moves to Microsoft Entra ID (`entra_auth.py` is built but not wired in).

| Call | What it does |
|---|---|
| `POST /auth/login` | Body `email` and `password` (email ignores case). Returns `token` and `expires_at`. Wrong email and wrong password give the same 401. Five wrong passwords lock that account for 15 minutes (429) |
| `GET /auth/me` | Who the token belongs to: `id`, `name`, `email`, `roles` |
| `POST /auth/password` | Change your own password (`current_password`, `new_password` of 8+ characters). Signs your other browsers out |
| `POST /auth/logout` | Ends this session |

Send the token on every other call as `Authorization: Bearer <token>`. A session lasts 7 days, and only a hash of the token is stored. A user with no `credential` row, or who is not `active`, cannot sign in. HR creates people and sets or resets passwords through `/admin/users` (see below); login returns `must_change` for a first or reset password.

`DEV_AUTH=true` (in `.env`, or set by the tests) also accepts `X-User-Id: <app_user id>` with no password. It must be off in production. `current_user` in `db.py` is the one function every endpoint depends on.
The web app's address for CORS is `WEB_ORIGIN` (default `http://localhost:5173`). Interactive docs at http://localhost:8000/docs.

Known limits: the lockout is per account, not per IP (add an IP limit at the proxy before going public), and there is no password reset by email.

## Time API (WH-20)

| Call | What it does |
|---|---|
| `GET /time/targets` | What the week grid can log time on: the tasks you can see (with their project) and the active charge codes shared with your team |
| `GET /time/week?on=YYYY-MM-DD` | The week's entries, status, per-day minutes, each day's status (`draft`, `submitted`, `approved`, `sent_back`), why a day was sent back and the approved minutes |
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

## HR options on an approved week

HR (the `hr` role) has two ways to fix an approved week, each with a required reason. HR can't use them on their own week, and a week with a pending edit request is refused until that is resolved.

| Call | What it does |
|---|---|
| `POST /hr/users/{user_id}/weeks/{week_start}/corrections` | **Correct directly.** Body: `reason` and `changes` (add, update, delete, as for edit requests). Checked against every time rule and applied at once; the week stays locked. Audited under the HR person's name |
| `POST /hr/users/{user_id}/weeks/{week_start}/send-back` | **Send back for re-approval.** Body: `reason` and optional `dates` (empty means every day with time). The week returns to `draft`; days not sent back stay approved and locked. The employee fixes the sent-back days and resubmits, and the manager approves them again. The reason shows in the week view (`day_reasons`) and in the approval's history |
Telling the employee by notification waits for WH-60.

## Leave (WH-40, WH-41)

Amounts are in hours: a full day is `org_settings.daily_expected_minutes` (normally 8 h) and a half day half of it. They are stored as whole minutes, like time entries. The leave year starts in `fy_start_month` (April).

| Call | What it does |
|---|---|
| `GET /leave/types` | The leave types (anyone signed in) |
| `POST /leave/types` | **HR.** Create a type: `name`, `paid` (false means LOP, loss of pay), `charge_code_id` (the leave time entries are booked to it), `accrual_per_month` and `carry_forward_cap` in hours, `attachment_after_days` |
| `PUT /leave/balances` | **HR.** Set `opening`, `accrued` or `adjusted` hours for a person, type and `leave_year` (only the fields you send change) |
| `GET /leave/balances?year=` | Your balances: opening, accrued, adjusted, used, pending and `available`. HR can add `user_id` for anyone's |
| `POST /leave/blackout-days`, `GET /leave/blackout-days` | **HR** adds a day nobody can take leave on (for example a release freeze or a year-end close); anyone can list them |
| `POST /leave/requests` | Apply: `leave_type_id`, `from_date`, `to_date`, optional `half_days` (`{date: first_half or second_half}`), `reason`, `attachment_key`. Creates the approval for your manager |
| `GET /leave/requests` | Your requests |
| `POST /leave/requests/{id}/withdraw` | Take back a request nobody has decided yet |
| `POST /leave/requests/{id}/cancel` | Cancel approved leave: gives the balance back and removes its time entries in one step |

Rules checked when you apply: only working days count (weekends and your location's holidays are skipped), the range stays inside one leave year, no blackout day, no overlap with other leave (two different half days on one day are fine), a reason for LOP leave, an attachment when a type needs one for longer leave, and enough balance for paid types (counting requests that are still waiting). Leave for dates already past is allowed and flagged `applied_after_dates`.

The manager decides it in the same inbox (`GET /approvals/inbox` rows have a `leave` summary). `POST /approvals/{id}/approve` deducts the balance and writes one read-only time entry (source `leave`) per day, in one transaction, and fails with 409 if the balance is gone or that week is already approved. `send-back` rejects it with a reason and changes nothing. Cancelling is refused when one of its weeks is already approved (HR has to correct that week).

Not built yet: monthly accrual by the worker, year-end carry forward, comp-off, the team calendar, and the Zoho import.

## Payslips (WH-50, WH-51)

HR uploads a month, checks how the files matched, then publishes. Employees see and download only their own.

| Call | What it does |
|---|---|
| `POST /payslips/batches` | **HR.** Multipart form: `month` (`2026-11`) and `files` (PDFs and/or ZIPs). A file is matched to an employee by the code at the start of its name, `<EMPLOYEE_CODE>_anything.pdf` (ignores case; folders inside a ZIP are ignored). Returns the report: `matched`, `unmatched` (with a reason: bad name, no such employee, not a PDF, too large) and `duplicates` (two files for one person; neither is kept). Uploading again to a draft month replaces it; a published month is locked (409) |
| `GET /payslips/batches/{id}` | **HR.** The same report |
| `POST /payslips/batches/{id}/publish` | **HR.** Makes it visible to employees. An empty batch (422) or one already published (409) is refused |
| `GET /payslips/mine` | Your published payslips (`id`, `month`), newest first |
| `GET /payslips/{id}/file` | The PDF, to its owner only. Anyone else (HR included) and anything unpublished gets 404. Every download is audited (`payslip`, `view`) |

Limits: 10 MB per PDF and 200 MB per upload. A file must start with `%PDF` (checked by content, not by extension). The PDFs are stored in Postgres for now (a `shortcut:` comment in `models.py` says when to move them to object storage). Form 16 and letters are not built.

## User administration (HR and admin)

| Call | What it does |
|---|---|
| `POST /admin/users` | Create a person: `employee_code`, `name`, `email`, a first `password` (8+ characters) and optionally `designation`, `department`, `location_id`, `manager_id`, `joined_on`, `roles` (default `employee`). The person must change that password: login returns `must_change: true` until they do |
| `GET /admin/users` | Everyone, with roles |
| `PATCH /admin/users/{id}` | Change only the fields you send. A manager must be an active user and the chain can't loop. `active: false` records the exit date and signs the person out everywhere (you can't deactivate yourself) |
| `PUT /admin/users/{id}/roles` | Set the roles |
| `POST /admin/users/{id}/password` | Reset a password: forces a change, clears a lockout and signs the person out everywhere |

Employee codes and emails are unique ignoring case. Only an **admin** can grant or remove the admin role or reset an admin's password, so HR can't make themselves an admin. Every change is audited, and no password or hash appears in a response or the audit log.

## Org admin (HR and admin)

Lists are replaced as a whole: what you send is what you get.

| Call | What it does |
|---|---|
| `POST/GET /admin/locations`, `POST/GET /admin/holidays` (`?location_id=`), `DELETE /admin/holidays/{id}` | Locations and their holidays (one holiday per location per date) |
| `POST/GET /admin/teams`, `PUT /admin/teams/{id}/members` (`user_ids`) | Teams and who is in them |
| `POST/GET /admin/charge-codes`, `PATCH /admin/charge-codes/{id}` (`name`, `active`), `PUT /admin/charge-codes/{id}/teams` (`team_ids`) | Charge codes and the teams they are shared with (this decides what `GET /time/targets` offers) |
| `POST/GET /admin/projects`, `PATCH /admin/projects/{id}`, `PUT /admin/projects/{id}/members`, `PUT /admin/projects/{id}/teams` | Projects. A new project gets the statuses Open, In progress, Done and a Backlog list. Members and the teams on a project decide who can see its tasks (`visibility.py`) |
| `POST /projects/{id}/tasks` | Add a task (`title`, optional `description`). HR, an admin or that project's manager can. The key is `<project key>-T<n>` |

Not built: clients and work orders, task owners, subtasks and comments, task editing.

## Roles (who can do what)

Roles are employee, manager, hr, finance and admin, and a person can hold several. The API checks them (`permissions.py`); the UI only hides what a role can't open. No sign-in gets 401, a missing role gets 403.

| Action | Needs |
|---|---|
| Log time, submit your week, see your own inbox and delegations | any signed-in user |
| Approve, send back, bulk approve, create a delegation | the **manager** role |
| Be the delegate of a delegation | the **manager** role (checked when the delegation is created) |
| Leave types and balances, payslip batches, `/admin/users`, `/admin/...` org data | the **hr** role (`/admin/...` also accepts **admin**, who alone can grant the admin role) |
| Reports, settings, audit-log viewer | not built yet. Use `Depends(require_roles("hr"))` when you add them |

On top of the role, approvals also check that the approval is **assigned to you** (your report's manager, a delegate, or the escalation target), and you can only touch your own time entries.

## Check before pushing

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
git config core.hooksPath api/.githooks         # one-time: runs lint and types on commit
```

CI (`.github/workflows/api-ci.yml`) runs the same checks against a Postgres service.
