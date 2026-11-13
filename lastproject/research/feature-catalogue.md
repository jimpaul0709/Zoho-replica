# WorkHub: full feature catalogue (brainstorm output)

## Context
The Zoho teardown is done (report: https://claude.ai/artifact/C9MTdN94GnNJ6pwshmiomr, notes in `research/`). We're replacing the three Zoho apps Ampera uses (Projects for timesheets, People for leave, Payroll for payslips) with one web tool. Base workflow unchanged; on top we add the best ideas from Odoo, Plane, OpenProject, Productive, Toggl, Clockify, Linear, Tempo and others, chosen to make tracking effortless and to be attractive if sold later.
Path: **architectural**. This catalogue gets approved first; then build approaches → spec (`docs/superpowers/specs/2026-11-12-workhub-design.md`) → writing-plans. The name "WorkHub" is a placeholder.

## Decisions so far
- Ampera-only for now (single company). Org-level settings (work week, holidays, branding) live in one place so multi-company can come later.
- Web only. **No mobile app. No monitoring or screenshots** (dropped).
- Payslips: HR uploads PDFs. No salary engine.
- Timesheet AI drafts read from the **Outlook/M365 calendar** and **Git commits/PRs**.
- Focus themes: effortless time capture, smart oversight, client-facing. No phasing for now: this is the full wish-list.

`★` = on-top feature (beyond Zoho/basic). Source tool in brackets.

## 1. People, roles and organisation
- Roles: Employee, Manager, HR, Finance, Admin. Access is scoped by reporting line and project membership. The menu hides anything a role can't open.
- Employee profile: ID, designation, department/practice, location, reporting manager, joining date.
- Teams (e.g. "Keysight – Accessibility") used for task assignment and reporting.
- Org settings: work week, working hours, holiday calendars per location, financial year (April–March).
- Sign-in with Microsoft 365 (SSO). Deactivating someone on exit keeps their history.
- ★ Approver delegation while away, with pending items rerouted automatically (Zoho users ask for this)
- Audit log on every record: who changed what, and when

## 2. Clients, projects and tasks
- Clients → SOW / work orders → projects. These replace the tags used today ("SOW-11101").
- Project key and task IDs (ATPL-106, AS1-T4), project groups/practices, status, public/private, project members with a project role
- Org charge codes for non-project time: Bench, Training, Proposal, Town hall…
- Tasks: lists/phases, custom statuses, owners or a team, priority, dates, rich description, attachments, comments with @mentions, subtasks
- Views: list, board, calendar. ★ Saved and shared views (Plane)
- ★ Status timeline: time spent in each status (Zoho task tab, worth keeping)
- ★ Project templates, including standard task lists for repeat engagements (Odoo)
- ★ Command palette (Ctrl-K) to jump anywhere, create a task or log time (Linear)

## 3. Time capture ★ (core differentiator)
- Week grid (Sun–Sat or Mon–Sun from org settings), with a billable/non-billable flag, notes, and "general log" entries without a task
- Rules: no future dates; submit the week; entries lock after approval and need an approved edit request to change
- ★ Global timer in the top bar. Start it, stop it, and it becomes an entry assigned to a task (Odoo)
- ★ Calendar view: drag to log time, resize an entry to change hours (OpenProject)
- ★ **AI-drafted day/week:** suggested entries come from Outlook meetings (matched to a project by title, attendees or client domain) and from Git commits/PRs (matched by repo or branch to a project or task). The employee accepts, edits or rejects each one, and nothing is auto-submitted (Tempo, ClickTime)
- ★ Copy last week, and pinned or favourite rows (Clockify, Harvest)
- ★ Approved leave and holidays fill the week automatically, so nobody logs them (fixes the Zoho "Absent vs 8 h" conflict)
- ★ Daily total coloured against the expected hours (Odoo)
- ★ Smart reminders: missing days, skipping leave and holidays; a "submit your week" nudge on Friday; nudges to approvers (Odoo, Clockify)

## 4. Leave
- Types with balances: Comp-off, Earned, LWP, PTO; accrual and carry-forward per type; April–March leave year
- Apply: date range, half-day per date, reason, attachment (e.g. medical note), balance preview before submitting
- Withdraw or cancel; leave can be applied after the dates with a flag
- ★ Comp-off request when someone works on a holiday or weekend
- ★ Team calendar showing who's out, with pending leave shown as tentative (Float)
- ★ Approval timeline visible in the list: approver, level, how long it took (Zoho hides this behind a "View" button)
- ★ Blackout days, i.e. "stress days", when leave is restricted (Odoo)
- ★ LWP / attendance summary export for payroll each month

## 5. Approvals inbox ★
- One queue for timesheets, leave, comp-off and edit-after-lock requests
- Bulk approve; Approve / Send back with a reason. Rejected timesheet entries reopen with the reason shown (Zoho users ask for this)
- Each item shows its age, with escalation when it passes the agreed approval time
- Act from the email or Teams message as well as in the app

## 6. Smart oversight ★
- ★ **Timesheet anomaly flags** (no vendor ships these):
  - a missing day
  - a week over the limit
  - hours logged on approved leave or a holiday
  - a charge code the person isn't assigned to
  - the same note copied every day
  - a sudden drop from the person's usual hours
- ★ Manager dashboard: team submission %, missing days, pending approvals, who's out this week, billable vs non-billable split
- ★ AI weekly project status: a summary from task changes, hours and comments that the manager edits before sharing (Asana, ClickUp)
- ★ "What changed since last week" on a project (OpenProject baseline)

## 7. Client-facing ★
- ★ Client portal users per project: read-only progress, milestones, a summary of approved hours, shared documents (Odoo)
- ★ Shareable status report as a branded link or PDF, built from the AI weekly status
- ★ Client request thread: the client raises a request, it becomes a task, and the client sees its status
- ★ Satisfaction rating requested when a milestone or task reaches a chosen stage (Odoo)

## 8. Payslips and documents
- HR bulk-uploads monthly PDFs, matched to people by employee ID, with a preview and a mismatch report before publishing
- Employee view: monthly tabs, amounts masked until clicked, download, full history
- Other documents: Form 16, letters. Access stays read-only after exit through an export
- A notification goes out when a new payslip is published

## 9. Notifications ★
- An in-app bell with grouping (one "5 entries approved for 10–14 Nov" instead of five), plus a daily digest email
- Per-event preferences (not just on/off per project); critical events are always delivered
- Microsoft Teams messages for approvals and reminders

## 10. Reports
- Timesheet compliance; hours by project, client, charge code and person; billable vs non-billable; leave usage and balances; approval turnaround
- Filters, saved reports, CSV/Excel export, scheduled email reports

## 11. Integrations and migration
- Microsoft 365: SSO, Outlook calendar (read-only, for AI drafts), Teams notifications
- GitHub/GitLab: commits and PRs for AI drafts, with repos mapped to projects
- ★ Zoho import: projects, tasks, time logs, leave balances and history, read via the Zoho connector or CSV, so switching over is painless

## 12. Quality bar
- Pages load in under 1 second, with search everywhere, dark mode, keyboard support and accessibility (WCAG AA)
- Nightly backups and an audit log

## Parked / out
- Parked: rates, utilization, profitability, budgets, capacity planner (Money & capacity), and a salary engine
- Out: mobile app, activity monitoring and screenshots

## Next steps after approval
1. Propose 2–3 build approaches (stack and structure) with a recommendation.
2. Present the design section by section: data model, flows, roles.
3. Write the spec, self-review it, get it approved, then run writing-plans.

## Verification
- Each feature traces to a Zoho gap (`research/zoho-research.md`), a pain point (`research/pain-points.md`) or a benchmark tool named above.
- The spec states, per feature, which role sees and does what.
