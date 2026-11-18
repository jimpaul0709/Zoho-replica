# WorkHub: Solo Release (to Dec 24, 2026)

## Problem
Ampera runs timesheets in Zoho Projects, leave in Zoho People and payslips in Zoho Payroll. WorkHub is meant to replace all three in one web app by Dec 24. The backend for time, approvals and leave is built, but there is no frontend, no real sign-in, no payslips and no deploy path. The work was planned for three people and is now done by one person with about 5 hours a day, so the plan has to shrink to what one person can finish.

## Evidence
- Repo state: 25 commits, API only. Migrations 0001 to 0005 and about 20 test files exist. There is no `web/` directory. Sign-in is still the dev-only `X-User-Id` header (`current_user` in `api/src/workhub_api/db.py`).
- Zoho pain points and teardown: `documentation/research/`.
- Capacity: about 27 working days from Nov 18 to Dec 24, at 5 hours a day, is about 135 hours. The old plan's remaining committed work was about 40 focus-days across three people. Assumption — the estimate for solo work needs validation after the first week via actual hours logged.

## Users
- **Primary:** Ampera employees (log and submit time, apply for leave, view payslips), managers (approve), and HR (leave types, balances, payslip upload, time corrections).
- **Builder:** one developer, about 5 hours a day, working with Claude.
- **Not for:** clients (no portal), finance reporting beyond a basic export, mobile users.

## Hypothesis
We believe a thin slice (sign in, log and submit a week, approve or send back, apply for and approve leave, view a payslip) will let Ampera drop Zoho for its first release.
We'll know we're right when HR can run one real month (time, leave and payslips) on WorkHub with no fallback to Zoho.

## Success Metrics
| Metric | Target | How measured |
|---|---|---|
| Sign-in and week logged end to end | Done by Fri Nov 20 | Demo against `workhub_1` |
| Full thin-slice journey in the UI | By Dec 11 | Manual run of the four journeys |
| HR dry run with real data | By Dec 21 | One month of time, leave and payslips |
| Release candidate | Dec 24 | CI green, migrations applied cleanly, rollback note written |

## Scope
**MVP (must)**
1. Sign-in version 1 (email and password, sessions) replacing the dev header.
2. Minimal frontend on Bun and React: week grid, approvals inbox, leave apply, payslip view.
3. Payslips: HR uploads a batch, files are matched by employee code, HR publishes, employees view their own.
4. Minimal org admin: users, roles, teams, charge codes and projects (API only, seeded where possible).
5. Hardening: permission and audit sweep, CI green, deploy and migration step, backup and rollback note.

**Should (cut first if late)**
- Notification bell only.
- Monthly leave accrual in the worker.
- Monthly LWP export.

**Out of scope**
- Tasks v2 (subtasks, comments), clients and work orders — deferred, projects work without them.
- Calendar view, global timer — nice to have, not needed to replace Zoho.
- Comp-off, anomaly flags, manager dashboard — after release.
- AI and Outlook/Git suggestions, weekly AI status — after release.
- Zoho data import — HR enters leave opening balances by hand at go-live.
- Reports, saved views, command palette, client portal — after release.
- Entra ID sign-in (version 2) — will mostly slip past Dec 24; keep `entra_auth.py` in mind.

## Delivery Milestones
| # | Milestone | Outcome | Status | Plan |
|---|---|---|---|---|
| 0 | Dedicated DB ready | Migrations 0001 to 0005 applied to `workhub_1` and seeded | pending | — |
| 1 | Sign in and log a week | A user signs in with email and password, logs and submits a week. **Due Fri Nov 20** | in-progress | .claude/plans/workhub-solo-release.plan.md |
| 2 | Approvals and leave in the UI | Manager approves or sends back; employee applies for leave; manager approves | pending | — |
| 3 | Payslips | HR publishes a batch; employees view their payslip | pending | — |
| 4 | Hardening and dry run | Security sweep, deploy with migrations, real-data dry run | pending | — |
| 5 | Buffer | Last 3 days kept for fixes | pending | — |

## Migrations (schema, Alembic)
- The chain 0001 to 0005 is clean and linear. The database is no longer shared: `api/.env` points at the dedicated `workhub_1` database, and `alembic current` shows no revision there, so it is empty and 0001 to 0005 still need applying (milestone 0).
- New migrations only as the MVP needs them: 0006 credentials and sessions, 0007 payslips and documents, 0008 notifications (only if kept).
- Each migration gets a downgrade, runs in CI, and is tried on a throwaway database before Azure. Take a backup before each production upgrade.
- Cleanup once the database is dedicated: remove the `include_object` filter in `migrations/env.py` and the shared-database note in the READMEs. Not urgent.
- Turn `DEV_AUTH` off before any real deploy.

## Working with Claude (5-hour days)
- **Per item:** `/plan` it, then build test-first (tdd-workflow). Keep each item to a half day or less.
- **Migrations:** the alembic skill, with database-reviewer on each one.
- **Frontend:** have Claude scaffold `web/` on Bun from the API's OpenAPI schema with a typed client, then build one screen at a time and check it in the browser.
- **Hardening:** security-reviewer and code-reviewer passes before each milestone; update the Word-doc build scripts that still say Entra-only.
- **Rhythm:** a short daily log of hours and what shipped, and a weekly check of this plan against real hours so cuts happen early.

## Open Questions
- [ ] Where does the app deploy (same Azure region as the database to avoid the 250 ms round trip)?
- [ ] Payslip file storage: MinIO locally and Azure Blob in production?
- [ ] Should sign-in v1 allow self-service password reset, or does HR set passwords?

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Frontend takes longer than estimated | High | High | Build only the four screens; generate the API client; cut the Should items first |
| Friday Nov 20 sign-in deadline is tight | Medium | Medium | Keep v1 to email and password and sessions, no extras |
| Azure latency slows development | Medium | Low | Develop against local Docker Postgres; test on Azure |
| Scope creep from Entra or extra features | Medium | Medium | Out-of-scope list above; check weekly |
| Solo bus factor | Medium | High | Keep README and docs current; daily log |

---
*Status: DRAFT — requirements only. Implementation planning pending via /plan.*
