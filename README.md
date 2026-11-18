# WorkHub

Project and leave management tool. One web app replacing Zoho Projects (timesheets), Zoho People (leave) and Zoho Payroll (payslips) for Ampera. Deadline: Thu 24 Dec 2026 (Dec 25 is a holiday). First working version: Dec 1.

## Repo layout

| Path | What it is |
|---|---|
| `documentation/docs/` | The 7 Word docs (Overview, PRD, Sprint Plan, Design, Architecture, FSD, NFSD) and their build scripts |
| `documentation/docs/superpowers/specs/2026-11-12-workhub-design.md` | Full design spec: data model, flows, build order |
| `documentation/research/` | Zoho teardown, pain points, pricing, feature catalogue |
| `api/` | Backend: FastAPI on uv (WH-01, built). The worker will live here too |
| `.github/workflows/api-ci.yml` | CI: lint, format check, mypy, pytest against a Postgres service |
| `web/` | Frontend (React on Bun). Not created yet, owned by Jayasree (WH-02) |

## How the pieces connect

```
Browser ──► web/ (React, Bun)  ──HTTPS/JSON──►  api/ (FastAPI)  ──►  Postgres (Azure, hosted)
                                                      │
                                                      └─► MinIO / S3-compatible storage (payslips, attachments; later)
```

- **Database:** hosted Azure Database for PostgreSQL. The API reads separate settings from `api/.env`: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_SSLMODE` (use `require` for Azure). `api/src/workhub_api/config.py` builds the connection URL from them.
- **Local Postgres is optional:** with no `.env`, the defaults point at the Docker Postgres in `api/docker-compose.yml`. CI uses that route, not Azure.
- **Secrets:** real credentials live only in `api/.env`, which is gitignored. `api/.env.example` holds placeholders only. Never commit `.env`.
- **Azure access:** the server firewall must allow your current IP, otherwise the connection times out.

## What exists so far (WH-01, 13 Nov)

- `api/`: uv project (Python 3.12) with FastAPI, SQLAlchemy 2, psycopg, Alembic, and dev tools pytest, ruff, mypy (strict).
- `api/src/workhub_api/main.py`: `GET /health`, which also runs `select 1` against the database.
- `api/tests/test_health.py`: runs against real Postgres. Verified passing against the Azure database.
- `api/docker-compose.yml`: local Postgres 16 and MinIO.
- `api/.githooks/pre-commit`: ruff and mypy on commit (turn on with `git config core.hooksPath api/.githooks`).
- `.github/workflows/api-ci.yml`: has not run yet because nothing is pushed.

## What exists so far (WH-03, 13 Nov)

- `api/docs/erd.md`: the database ERD (Mermaid diagrams, migration plan, rules the database enforces).
- `api/src/workhub_api/models.py`: SQLAlchemy models for the 25 core tables (organisation, people, projects, tasks, time, approvals, audit, job). The user table is `app_user` because `user` is reserved in Postgres.
- `api/migrations/versions/0001_core_schema.py`: the first Alembic migration, **applied to the Azure database**. It includes the append-only trigger on `audit_event`.
- `api/tests/test_schema.py`: checks the database rules (one task or charge code per entry, minutes 1–1440, audit cannot be changed).
- Leave, payslips and notifications tables come in later migrations (see the ERD).

## What exists so far (WH-20, WH-30, WH-07, WH-32, 16 Nov)

- `api/src/workhub_api/timesheets.py`, `approvals.py`: the time API and the approval engine for weeks (see `api/README.md`).
- `api/src/workhub_api/jobs.py`, `worker.py`: the job queue and the worker (`uv run python -m workhub_api.worker`).
- `api/src/workhub_api/routing.py`, `delegations.py`: delegation, due dates in working days, escalation. Migration `0002` adds `org_settings.approval_due_working_days`.
- `api/src/workhub_api/seed.py`: sample data (Jay, Jana, Jim). Run once with `uv run python -m workhub_api.seed`.
- `api/src/workhub_api/permissions.py`: role checks (managers approve and delegate). `edit_requests.py` (WH-22): changing a locked week through approval. Migration `0003` adds the `edit_request` table.
- **Shared database note:** the Azure database also holds another module's tables (`users`, `employees`, `roles`, `organizations` and more, with their own `people_alembic_version`). Our Alembic ignores tables that are not in our models (`migrations/env.py`), so it never drops them. Check with the team how our `app_user`, `team` and `holiday` tables relate to their `users`, `teams` and `holidays`.
- Speed note: the shared Azure database answers in about 250 ms per round trip from a laptop, so each API call takes 1 to 5 seconds in development. That is distance, not code. In the same Azure region it should take a few milliseconds. Keep the API and the database in one region when deploying.

## Run it

Backend first (full details in `api/README.md`):

```bash
cd api
cp .env.example .env                           # point at local Docker or Azure Postgres
docker compose up -d db minio                  # skip db if .env points at Azure
uv sync
uv run alembic upgrade head
uv run python -m workhub_api.seed              # optional sample data; sign in as jim@example.com / workhub-dev-1
uv run uvicorn workhub_api.main:app --reload   # http://localhost:8000 (docs at /docs)
uv run python -m workhub_api.worker            # optional, in a second terminal
```

Then the frontend:

```bash
cd web
bun install
bun run dev                                    # http://localhost:5173
bun run gen:api                                # after API changes: regenerate src/api-types.ts from openapi.json
```

## What is next (backend lane, Jim)

| When | Item |
|---|---|
| now | Push so CI runs once |
| 16–20 Nov | **WH-03** schema is drafted and migrated; remaining: review with the team, then audit-event helper (write one row on every change) |
| 23–27 Nov | **WH-20** time API: entries, week, rules, submit and lock |
| 27 Nov–1 Dec | **WH-30** approval engine v1: built for weeks (inbox, approve and lock, send back with a reason, history); leave and edit requests plug in later |
| 2–10 Dec | WH-07 job worker, WH-32 delegation and escalation, WH-33 inbox depth (filters, bulk approve, timeline) are built |
| 14–18 Dec | WH-90 seed data and four end-to-end journeys, WH-91 security sweep |
| 21–23 Dec | WH-94 buffer, release checks, basic load test |

Others: Janagan owns sign-in (WH-04: version 1 is email and password, version 2 is Microsoft Entra ID, which needs the app registration), org, projects, payslips and notifications. Jayasree owns the frontend repo, app shell, week grid, leave and accessibility. Full plan: `documentation/docs/WorkHub_Sprint_Plan_v0.1.docx`.
