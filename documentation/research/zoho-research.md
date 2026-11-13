# Zoho teardown: Projects + People + Payroll (as used at Ampera)

2026-11-12. Read-only walkthrough of our live portals (Employee profile), the Zoho Projects API connector, Zoho pricing pages, and ~90 community/review sources.
Detail files: [connector-findings.md](connector-findings.md), [pricing.md](pricing.md), [pain-points.md](pain-points.md), screenshots in [screens/](screens/).

## Headline findings
1. **Zoho Projects at Ampera is a timesheet charge-code system.** Milestones, issues, dependencies, comments and attachments are unused (0 across all 16 projects). Value sits in time logs: billable/non-billable, approval status, and an "Organizational Tasks" project of 16 standing codes (Bench, Proposal ≈1,609 h, Training…). Tags fake a client/SOW model ("SOW-11101").
2. **The three apps disagree about the same day.** On Tue 10 Nov, Projects has 8 h logged and approved, while People shows "Absent" with Attendance "Present: 0". Leave Summary says "Absent: 0". People also has its own Time Tracker/Timesheets, which are empty. Two time systems, no sync.
3. **Approvals exist but are hidden.** The People leave approval timeline (approver, level 1/1, "Acted in 4 days") sits behind a "View" button. The list shows only a green tick, with no approved-by/at column, no escalation on a 4-day wait, and an optional reason. In Projects, approvals arrive as 5 identical notifications with no hours or dates.
4. **Notifications: 99+ unread in Projects.** Preferences are just an on/off switch per project, with no per-event control and no digest.
5. **Permissions leak into the UI.** Employees see a "Timesheets" menu item that opens "Permission Denied".
6. **Plan:** Projects + Bug Tracker are on **Enterprise** (₹700/user/mo monthly, ₹630 annual). The People and Payroll plans aren't visible to an Employee profile. Multi-user timesheets would need Ultimate (₹980–1,050).

## User's idea vs. what's needed
| Area | The idea had | Missing (small but real) |
|---|---|---|
| RBAC | roles | Scope by reporting line and project membership; hide what you can't open; "why can't I see this" |
| Projects | create project, add members | Project key + task IDs (ATPL-106, AS1-T4); client → SOW/work order → project; project groups; status; public/private; standing org charge codes; team-based task assignment |
| Timesheet | fill timesheet | Week grid (Sun–Sat per org config); billable/non-billable; notes; per-entry approval status; no future dates; log for a task or a "general log"; timer; missing-day reminders; rejection reason sent back to the entry; lock after approval; "approved by/at" |
| Leave | apply leave | Types with balances (CL/EL/LWP/PTO/Comp-off); fiscal leave year; half-day per date; reason + attachment; approval timeline visible in the list; delegation/escalation SLA; holidays per location; leave pre-fills timesheet and attendance |
| Payslip | view payslip | Masked amounts by default; monthly tabs; download PDF + all history (also after exit); Form 16; investment declaration window (admin opens/locks); proof upload; salary structure |
| Cross-cutting | — | One approvals inbox (bulk, comments); grouped notifications + digest; per-event prefs; activity stream + status timeline per record; built-in reports (utilization, timesheet compliance, leave, payroll register); fast pages (Home spinner > 11 s) |

## Suggested MVP scope (input for the brainstorm, not a spec)
- **Must:** org/users/roles (Employee, Manager, HR, Finance, Admin); clients → projects → tasks with keys; org charge codes; week timesheet with billable flag and approval; leave types/balances/apply/approve with timeline; holiday calendar + work-week shared by leave and timesheets; leave auto-fills the timesheet; payslip view/download (upload or generate from a salary structure, decide later); a single approvals inbox; in-app notifications with digest; audit trail on every record.
- **Should:** reminders for missing timesheet days; delegation and escalation; utilization and compliance reports; CSV export; investment declarations.
- **Later:** Gantt, milestones, issue tracker, blueprints, attendance check-in/geo, full payroll engine (statutory calc).
- **Out of scope:** mobile app (web only).
- **Payslip note:** full-history download, proof uploads and salary-structure view are suggestions; they still need checking by someone with Payroll admin access.

## Gaps in this research
- Reddit and Quora unreachable (blocked; Quora needs login). Evidence is from Zoho forums, review-site snippets, app stores, blogs.
- Employee profile only: no admin settings, billing page, or the Timesheets approval module. People/Payroll plan tiers unknown.
- Salary figures deliberately not viewed or captured.
