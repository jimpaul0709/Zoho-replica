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

Run it: see `api/README.md`.

## What is next (backend lane, Jim)

| When | Item |
|---|---|
| now | Set `POSTGRES_SSLMODE=require` in `.env`; turn on the commit hook; push so CI runs once |
| 16–20 Nov | **WH-03** core database schema and Alembic migrations (tables in the design spec; time as integer minutes; audit event on every change) |
| 23–27 Nov | **WH-20** time API: entries, week, rules, submit and lock |
| 27 Nov–1 Dec | **WH-30** approval engine v1: route, approve, send back with a reason, history |
| 2–10 Dec | WH-07 job worker, WH-32 delegation and escalation, WH-33 inbox depth |
| 14–18 Dec | WH-90 seed data and four end-to-end journeys, WH-91 security sweep |
| 21–23 Dec | WH-94 buffer, release checks, basic load test |

Others: Janagan owns sign-in (WH-04, needs the Entra ID app registration), org, projects, payslips and notifications. Jayasree owns the frontend repo, app shell, week grid, leave and accessibility. Full plan: `documentation/docs/WorkHub_Sprint_Plan_v0.1.docx`.
