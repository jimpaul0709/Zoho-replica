# WorkHub: design spec

Date: 2026-11-12 · Status: draft for review · "WorkHub" is a placeholder name.

## 1. Purpose
Ampera uses three Zoho apps: Projects (mostly as a timesheet charge-code system), People (leave) and Payroll (payslips). WorkHub replaces them with one web tool built by us. The base workflow stays the same. On top, it adds the features that make tracking effortless, catch problems early and, optionally, let clients see progress.

Research behind this spec:
- `research/zoho-research.md`: teardown and gaps
- `research/pain-points.md`: ~90 user complaints with sources
- `research/pricing.md`
- `research/feature-catalogue.md`: the approved feature list
- Report: https://claude.ai/artifact/C9MTdN94GnNJ6pwshmiomr

Odoo, Plane and OpenProject are used as references for behaviour only. No code is forked from them.

## 2. Scope decisions
| Decision | Choice |
|---|---|
| Who it's for | Ampera only (single company). Org settings are kept in one table so multi-company is possible later. |
| Platforms | Web only. No mobile app. |
| Monitoring | None. No desktop agent, activity capture or screenshots. |
| Payslips | HR uploads PDFs. No salary calculation. |
| AI timesheet drafts | From the Outlook/M365 calendar and Git commits/PRs. Always suggestions that the user confirms. |
| Client portal | Optional add-on module, **off by default**. The core app never depends on it. |
| Parked | Rates, utilization, profitability, budgets, capacity planner, salary engine. |

## 3. Architecture
```
Browser ── React + TS (Bun, Vite) ──HTTPS/JSON──► FastAPI (uv) ──► Postgres
                                                     │
                                  Worker (same uv codebase, second process)
                                                     │
                  M365 (Entra SSO, Outlook, Teams) · GitHub/GitLab · LLM API · S3-compatible storage
```
- **web/**: React + TypeScript, built and run with Bun (Vite). It contains screens only. API types are generated from FastAPI's OpenAPI schema.
- **api/**: a FastAPI app managed with uv. It has one Python package per module: `people`, `projects`, `time`, `leave`, `approvals`, `payslips`, `notifications`, `reports`, `integrations`, `audit`, and the add-on `client_portal`. Each module owns its models, rules (services) and routes.
- **Worker**: the same Python package, started with `uv run python -m app.worker`. It has no HTTP routes. It processes a Postgres-backed job table (no Redis) and runs the schedules listed in §6.7.
- **Storage**: Postgres for all data, including jobs and audit. Files (payslips, attachments) go in S3-compatible storage (Azure Blob or MinIO) and are served through short-lived signed URLs.
- **Rules that apply everywhere**:
  1. One approval engine (§6.4) is used by every approvable thing.
  2. Every create, update and delete writes an `audit_event`.
  3. Permissions are enforced in the API. The UI only hides what a role can't open.
  4. AI output is always a draft that a person accepts or edits.

## 4. Roles and access
| Role | Sees | Does |
|---|---|---|
| Employee | Own time, leave, payslips, suggestions; projects they belong to | Log time, submit week, apply leave and comp-off, accept or reject suggestions |
| Manager | Everything an Employee sees, plus direct and indirect reports' time and leave, and projects they manage | Approve or send back, delegate approvals, edit and share weekly status, team dashboard |
| HR | Everyone's profiles, leave and balances; payslip batches | Manage leave types, holidays, blackout days and balance adjustments; upload and publish payslips |
| Finance | Time reports for everyone; monthly LWP export | Reports and exports (read-only otherwise) |
| Admin | Settings, roles, integrations, audit log, failed jobs | Configure everything. Admins can't see payslip contents unless they also hold HR. |

- A user can hold several roles.
- Suggestions and their evidence (meeting titles, commit messages) are visible **only to their owner**.
- Managers see only what was submitted.

## 5. Data model
All tables have `id`, `created_at` and `updated_at`. Time is stored as integer minutes and dates as `date`.

**Org and people**
- `org_settings`: work week days, start of week, daily expected minutes, financial-year start month (4), branding, `client_portal_enabled` (default false).
- `location` → `holiday` (date, name).
- `user`: employee_code, name, email (unique, matches M365), designation, department, location_id, manager_id, joined_on, exited_on, active.
- `role_assignment`: user_id, role.
- `team` and `team_member`.

**Work**
- `client` → `work_order` (code e.g. "SOW-11101", start and end dates) → `project`:
  - fields: key (e.g. "ATPL-106", unique), name, group, status, visibility (public/private), manager_id
  - `project_member`: user_id, project role; `project_team` links whole teams.
- `task_list` → `task`:
  - fields: key (e.g. "AS1-T4"), title, description (rich text), status_id, priority, start and due dates, parent_id, is_milestone (milestones are tasks with this flag set)
  - `task_owner`, which points to a user or a team
  - `task_status`, defined per project (name, order, is_closed)
  - `comment` (with @mentions) and `attachment`
- `charge_code`: code, name, active. `charge_code_team` controls who can use it.
- `saved_view`: owner, scope, filters as JSON, and whether it's shared.
- `project_template`: name, plus its task lists and tasks as JSON.

**Time**
- `timesheet_week`: user_id, week_start, status (draft · submitted · approved · sent_back), locked_at.
- `time_entry`:
  - fields: user_id, date, minutes, task_id or charge_code_id (exactly one), billable, notes
  - source: manual · timer · calendar · git · leave · holiday
  - week_id, plus `sent_back_reason` (nullable)
- `running_timer`: user_id (unique), task_id or charge_code_id, started_at.
- `suggestion`: user_id, date, minutes, proposed target, source (calendar/git), evidence as JSON, status (pending · accepted · rejected), and time_entry_id once accepted.
- `edit_request`: week_id, requested changes, reason. It goes through approval.
- `anomaly`: week_id, rule, detail, status (open · dismissed with a note).

**Leave**
- `leave_type`: name, paid, accrual per month in minutes or days, carry-forward cap, needs-attachment-after-N-days.
- `leave_balance`: user_id, type_id, leave year, opening, accrued, used, adjusted. `available` is computed.
- `leave_request`: user_id, type_id, from and to dates, per-day portion as JSON (full/first-half/second-half), reason, attachment, status, applied_after_dates flag.
- `comp_off_request`: user_id, worked date, minutes, reason, status.
- `blackout_day`: date, scope (org/team), note.

**Approvals**
- `approval`:
  - fields: subject_type (week · leave · comp_off · edit_request), subject_id, requester_id, approver_id, level, status (pending · approved · sent_back · cancelled), due_at, reason
  - `approval_step` records every action with who and when.
- `delegation`: from_user, to_user, start date, end date.

**Payslips and documents**
- `payslip_batch`: month, uploaded_by, status (draft · published), and a match report as JSON.
- `payslip`: batch_id, user_id, file_key. `document`: user_id, type (form16 · letter), file_key, year.

**Notifications, audit, integrations**
- `notification`: user_id, event, payload, group_key, read_at.
- `notification_pref`: user_id, event, channels (in_app · email · teams · digest).
- `audit_event`: actor_id, entity, entity_id, action, before and after as JSON, at.
- `integration_account`: user_id, provider (m365/github/gitlab), encrypted token, status.
- `repo_link`: repo, project_id or task_id, plus an optional branch pattern.
- `status_report`: project_id, week_start, AI draft, edited text, status (draft · final).
- `job`: kind, payload, run_at, attempts, last_error, status.

**Client portal add-on** (created only by the add-on's migrations)
- `client_user`: client_id, email, name. It's a separate identity from `user`.
- `client_project_share`: client_user_id, project_id, what is visible.
- `client_request`: project_id, client_user_id, title, body, task_id once converted, status.
- `rating`: project_id, task or milestone, client_user_id, score (1–5), comment.
- `status_report_share`: report_id, token, expires_at.

## 6. Features and flows

### 6.1 Organisation and people
- HR and Admin manage users, locations, holidays, teams and roles.
- Users sign in with Microsoft Entra ID. A user's first sign-in links to the `user` row whose email matches.
  - **Update 17 Nov 2026:** Entra ID is version 2. Version 1 signs in with email and password. This replaces "no local passwords" (NFSD SEC-01) for version 1; the build scripts and the generated PRD, FSD and NFSD still say Entra only and need updating.
- When someone leaves, `exited_on` is set and they're deactivated. Their history and payslips are kept.

### 6.2 Projects and tasks
- Clients → work orders → projects. Project keys are typed in by people; task keys are generated as `<prefix>-T<n>`.
- Views are list, board and calendar, with saved and shared views.
- The task page shows comments, attachments, subtasks, an activity history (from `audit_event`) and a status timeline (time spent in each status, from `audit_event`).
- "What changed since <date>" on a project lists audit events grouped by task.
- Project templates create the task lists and tasks.
- The command palette (Ctrl-K) can jump to a project, task or person, create a task, start the timer, or open this week.

### 6.3 Time capture
- **Week view**:
  - rows are a task or charge code plus a billable flag; columns are days; there's a notes cell
  - the day total is coloured against the expected hours
  - weeks start on the day set in `org_settings`
- **Calendar view**: drag to create an entry and resize it to change its minutes.
- **Timer**: one per user, started from the top bar. Stopping it creates an entry with source `timer`, rounded to the minute.
- **Rules**:
  - entries can't be for future dates
  - a day can't go over 24 h
  - each entry targets exactly one task or charge code
  - charge codes are only available to teams they're shared with
- **Pre-fill**: when leave is approved or a holiday applies, the system writes entries with source `leave` or `holiday`. These are read-only in the grid.
- **Copy last week**: copies the rows (targets and billable flags) without the hours. Pinned rows always appear.
- **Suggestions (AI drafts)**:
  - **Outlook:** a nightly sync plus an on-demand "refresh" reads the user's calendar for the week. Each accepted or tentative meeting becomes a suggestion. The project is matched by, in order: a project key in the title, then attendees' email domains mapped to a client, then the user's history. A meeting with no match gets no target, and the user picks one.
  - **Git:** commits and PRs authored by the user are grouped per repo per day. `repo_link` maps them to a project or task, and a task key in the branch or commit message overrides that. Minutes are estimated from the gap between the first and last commit, capped at the day's remaining hours, and shown as an estimate.
  - Suggestions appear in a side panel with their evidence. The user can Accept (it becomes an entry), Edit-then-accept, or Reject. Suggestions are never submitted automatically.
  - The LLM is only used to tidy notes and pick between candidate projects. Matching rules run first.
- **Submit week**: the week becomes `submitted` and creates an approval (§6.4). Weeks with open anomalies can still be submitted, and the anomalies are shown to the approver.
- **Lock**: an approved week is locked. Changes go through an `edit_request` that needs approval.

### 6.4 Approval engine and inbox
- **Routing:** an approval goes to the requester's manager. If the manager has an active delegation, it goes to the delegate instead.
- **When a delegation starts:** pending approvals move to the delegate.
- **Actions:**
  - Approve.
  - Send back, which needs a reason. For weeks, the reason is pinned on the selected entries and the week returns to `draft`.
- **Escalation:**
  - `due_at` is 2 working days after the request by default; this can be set in org settings.
  - When an approval passes `due_at`, it's reassigned to the approver's manager and both people are notified.
  - Every action is recorded as an `approval_step`.
- **The inbox** is one queue for weeks, leave, comp-off and edit requests:
  - it has filters and bulk approve
  - each row shows its age and any anomaly flags
- **Approving outside the app:** approve and send-back links in emails and Teams messages open the item already authenticated, and the action needs one confirm click.

### 6.5 Leave
- **Leave year:** runs April–March. Accrual runs monthly in the worker, and carry-forward is applied at year end up to the type's cap.
- **Apply form:**
  - shows the balance after the request before submitting
  - supports half days per date
  - the reason is required for unpaid leave
  - an attachment is required when a sick-type leave is longer than N days
  - leave on a blackout day is blocked, with a message saying why
- **Leave applied after the dates** is allowed but flagged.
- **Once submitted,** pending leave shows as tentative on the team calendar.
- **On approval,** one transaction:
  - deducts the balance
  - writes the leave time entries
  - records the timeline, which also shows in the list as the approver's name and how long it took
- **Cancelling or withdrawing** approved leave reverses all three in one transaction. If the week is already locked, the cancellation creates an edit request.
- **Comp-off:** time logged on a holiday or weekend shows a "Request comp-off" action. Approval credits the comp-off balance.
- **Finance's monthly export** shows LWP days and leave taken per employee.

### 6.6 Smart oversight
- **Anomaly rules** run when a week is submitted and nightly. They're stored in `anomaly`.
  1. A working day with no entries and no leave or holiday.
  2. A week over a limit (default 50 h).
  3. Time logged on an approved leave or holiday day.
  4. A charge code or project the user isn't a member of.
  5. The same note on 5 or more days in a week.
  6. A week below 60% of the user's 8-week average.
- **Approvers** see the flags and can dismiss one with a note.
- **The manager dashboard** shows, for the selected week and team: submission %, missing days, pending approvals, who's out, and billable versus non-billable minutes.
- **Weekly project status:**
  - On Friday the worker drafts a status per active project from task changes, hours by person and new comments, and saves it as a `status_report` draft.
  - The project manager edits it and marks it final. It stays internal unless the client portal add-on shares it.

### 6.7 Notifications and reminders
- **Bell:** in-app notifications are grouped by `group_key`, for example "5 entries approved, 10–14 Nov".
- **Daily digest email** at 09:00 local time.
- **Teams messages** for approvals and reminders.
- **Preferences:** set per event and per channel. Critical events (approval requested, approved, sent back, payslip published) always appear in-app.
- **Worker schedules:**
  - missing-day reminder on working days at 10:00, skipping leave and holidays
  - "submit your week" on the last working day of the week at 16:00
  - approver digest at 09:00
  - escalation check every hour
  - accrual on the 1st of each month
  - Outlook and Git sync nightly
  - weekly status draft on the last working day at 15:00
  - anomaly sweep nightly

### 6.8 Payslips and documents
- **Upload:**
  - HR uploads a ZIP or several PDFs for a month.
  - Files are matched by employee code in the filename (`<CODE>_*.pdf`).
  - A preview lists matched, unmatched and duplicate files. HR fixes the problems, then publishes.
- **On publish,** each employee gets a notification.
- **Employee view:**
  - one tab per month, with amounts hidden in the page summary until clicked
  - the PDF opens through a signed URL
  - full history and a "download all" ZIP
- **Exited employees** can't sign in. HR can generate a ZIP of all their documents.
- **Audit:** every payslip view and download is logged.

### 6.9 Reports
- **Reports:**
  - timesheet compliance
  - hours by project, client, charge code and person
  - billable versus non-billable
  - leave usage and balances
  - approval turnaround
- **Options:** filters, saved reports, CSV and Excel export, and scheduled email delivery (weekly or monthly).

### 6.10 Integrations and migration
- **M365:** Entra ID SSO; Graph API calendar read with delegated permission and per-user consent; Teams messages through an incoming webhook or bot.
- **GitHub/GitLab:** each user connects their own account (OAuth). Admins set up `repo_link` mappings.
- **Zoho import (one-off):**
  - What it imports: projects, tasks, time logs, users, leave types and balances, through the Zoho Projects API connector or CSV.
  - It runs as a dry run first and prints a report of counts and mismatches.
  - It's safe to re-run, keyed on Zoho IDs.

### 6.11 Client portal add-on (off by default)
- **Switch:** `org_settings.client_portal_enabled` turns it on.
  - When off, the add-on's routes return 404, its menu items and jobs don't exist, and its tables sit unused.
  - The core features in §6.1–6.10 have no imports from `client_portal`.
- **Identity:**
  - Client users are a separate table with a separate sign-in (an email magic link with a 15-minute token) and a separate session cookie scope.
  - They can't reach any employee API.
- **What a client user sees** on projects shared with them:
  - progress (tasks by status, milestones)
  - an approved-hours summary per week, not per person unless the project manager enables it
  - final status reports
  - shared documents
- **What they can do:**
  - raise a request, which the project manager can convert to a task, after which the client sees its status
  - comment on their own requests
  - rate a task or milestone when it reaches a stage the project manager has chosen
- **Sharing a status report:** a final report can be shared as a link that expires (token) or downloaded as a PDF.

## 7. Errors and data safety
- **API errors** use one JSON shape: `{code, message, fields?}`. The UI shows `message` as a plain sentence.
- **Atomic operations:** approval actions, balance changes, the leave → time entry move and payslip publishing each run in a single database transaction.
- **Jobs** retry 3 times with exponential backoff, then show in the admin "failed jobs" list with the error and a retry button.
- **Integration failures** (expired consent, rate limits): suggestions stop for that user and they see a "reconnect" banner. Logging time keeps working.
- **Uploads:**
  - the file type is checked by content, not just the extension
  - limits are 10 MB per file and 200 MB per ZIP
  - stored file names never come from user input
- **Secrets:** integration tokens are encrypted at rest, and secrets are read from the environment.

## 8. Testing
- **pytest** for module rules:
  - the approval engine: routing, delegation, escalation, send-back
  - accrual and carry-forward
  - leave → time entries and the reversal on cancel
  - lock and edit requests
  - each anomaly rule
  - suggestion matching
  - payslip filename matching
- **API tests** run against real Postgres (Docker) using the seed data.
- **Playwright end-to-end journeys:**
  1. Log and submit a week with an accepted suggestion.
  2. Approve one week and send another back with a reason.
  3. Apply leave, approve it, and check the timesheet is pre-filled.
  4. Upload and publish a payslip batch, then view it as the employee.
  5. With the add-on on, a client signs in, sees a shared report and raises a request. With it off, the portal returns 404.
- **Seed data** is modelled on Ampera: charge codes (Bench, Training, Proposal…), leave types (Earned, PTO, LWP, Comp-off), 2 locations, 3 teams, ~20 users.

## 9. Build order
Everything in §6 is in scope. This order says what gets built first so each step is usable on its own. It doesn't drop any feature.
1. **Foundation:**
   - repo layout (`web/` with Bun, `api/` with uv)
   - Postgres and migrations
   - Entra SSO
   - users, roles and org settings
   - the audit log
   - the job worker
   - the seed script
2. **Work and time:** clients, work orders, projects, tasks, charge codes; the week grid, timer, calendar view and copy last week; submit week.
3. **Approval engine and inbox:** routing, delegation, escalation and send-back, wired to weeks and edit requests.
4. **Leave:** types, balances, accrual, apply, approve, leave → timesheet pre-fill, comp-off, team calendar, LWP export.
5. **Payslips and documents.**
6. **Notifications and reminders:** bell, digest, Teams, preferences, and the worker schedules.
7. **Oversight:** anomaly rules, manager dashboard, weekly AI status, "what changed".
8. **Suggestions:** Outlook and Git sync, matching, and the suggestions panel.
9. **Reports, saved views, command palette, Zoho import.**
10. **Client portal add-on.**

## 10. Out of scope
Mobile apps; activity monitoring and screenshots; salary calculation; rates, utilization, profitability, budgets and the capacity planner; multi-company; offline use.
