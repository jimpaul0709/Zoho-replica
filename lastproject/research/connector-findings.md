# Zoho Projects: what our portal actually looks like (read-only connector, 2026-11-12)

## Plan and portal
- Projects plan: **Enterprise**; Bug tracker plan: **Enterprise** (from `get_portal_details.plan_details`).
- The account used has the **Employee** profile, not admin. Billing and admin settings will likely be hidden in the UI.
- Timezone Asia/Kolkata; storage on Zoho WorkDrive; date format MM-dd-yyyy.
- Business hours 09:00–18:00. **Working days are set to Sun–Thu with Fri/Sat weekends**, which looks like a misconfiguration for an Indian office. Worth noting: our replica needs a proper per-org work-week and holiday calendar.

## How the org actually uses Projects
- Project **keys** (ATPL-106 …) and task prefixes (AS1-T4, OT1-T10). Human-readable IDs matter.
- **Project groups** in use: "Data Science and Analytics", "Internal", "Ungrouped". These act like departments or practices.
- **Tags carry billing codes**: "SOW-11101", "SOW - 99902", "COE", "Bench - Learning & Development". The org has no first-class client/SOW/work-order concept, so tags are being misused for it.
- Public vs. private projects; `is_strict_project`; a budget tracking method of `project_hours`.
- Project statuses: Active / In Progress / Completed (custom, colour-coded).
- **Milestones: 0 and issues: 0 across every project.** These features go unused.
- "Organizational Tasks" (ATPL-46) is a **charge-code project**: 16 standing tasks (Bench, Induction, Idle Time, Training, Town Hall, Recruitment, Interviews, Proposal/Presentation, Travel, Audit, BCP/DR, …). Owner is "Unassigned User"; tasks are assigned to **teams** (client and work-order teams such as "Keysight - …", "LearningMate-…-WO002", "Freshers"). People just log time against them.
  - "Proposal/Presentation" alone has about 1,609 h logged; "Bench" about 308 h.
- Delivery projects (e.g. ATPL-106) use task lists as phases ("Discovery And Planning", "Development", "General"), custom statuses (Open / In Progress / In Review / Closed), multiple owners, priority, rich-text descriptions, and billing type (none / billable / non-billable).
- Every task carries `log_hours {billable, non_billable, total}`. **Timesheets are the core of how the org uses Projects.**
- Comments, attachments, subtasks, reminders, recurrence, dependencies: essentially unused (`association_info` is all false).

## Implications for the replica
1. Timesheet first: charge codes (org-level non-project activities), billable vs. non-billable split, and team-based task visibility.
2. Clients → SOWs/work orders → projects should be first-class, not tags.
3. Project key + task prefix IDs.
4. Gantt, milestones, issue tracker, and blueprints can be deferred, since nobody uses them today.
5. Work-week and holiday calendar per org (and per location), shared by Leave and Timesheets.
