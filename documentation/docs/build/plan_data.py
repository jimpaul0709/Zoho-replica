"""Single source of truth for the WorkHub plan: calendar, team, backlog, capacity.
Every document and chart imports this, so dates, owners and estimates never disagree."""
from datetime import date, timedelta

FOCUS = 0.7                      # share of a working day that is focused build time
HOLIDAYS = {date(2026, 12, 25)}  # Christmas, from the Zoho People holiday list
START, DEC1, DEADLINE, LAST_DAY = date(2026, 11, 13), date(2026, 12, 1), date(2026, 12, 25), date(2026, 12, 24)


def workdays(a, b):
    d, out = a, []
    while d <= b:
        if d.weekday() < 5 and d not in HOLIDAYS:
            out.append(d)
        d += timedelta(days=1)
    return out


ALL_DAYS = workdays(START, LAST_DAY)
IDX = {d: i for i, d in enumerate(ALL_DAYS)}

TEAM = {
    "JP": dict(name="Jim", lane="Core engine", focus="Database, time capture, approval engine, hardening"),
    "JK": dict(name="Janagan", lane="Platform and work", focus="Sign-in and access, organisation, projects and tasks, payslips"),
    "JS": dict(name="Jayasree", lane="Experience and leave", focus="App shell and design system, week grid, leave, accessibility"),
}
OWNER_COLOR = {"JP": "#002060", "JK": "#A82080", "JS": "#7870B0"}

SPRINTS = [
    dict(n=1, name="Foundation", start=date(2026, 11, 13), end=date(2026, 11, 20),
         goal="Everyone can sign in, the database and app shell exist, and all three of us can build in parallel."),
    dict(n=2, name="Thin slice to Dec 1", start=date(2026, 11, 23), end=date(2026, 12, 1),
         goal="Sign in, see projects and tasks, log a week, submit it, and a manager approves or sends it back."),
    dict(n=3, name="Leave and approval depth", start=date(2026, 12, 2), end=date(2026, 12, 11),
         goal="Leave types, balances and applying; delegation, escalation and bulk approval; clients, work orders and org settings."),
    dict(n=4, name="Payslips and leave approval", start=date(2026, 12, 14), end=date(2026, 12, 18),
         goal="Payslip upload and employee view; leave approval writes into the timesheet; team calendar; end-to-end tests. Feature freeze."),
    dict(n=5, name="Hardening and release", start=date(2026, 12, 21), end=date(2026, 12, 24),
         goal="Notification core, accessibility pass, UAT fixes, handover. Release candidate on Dec 24, the last working day before the Dec 25 holiday."),
]
for s in SPRINTS:
    s["days"] = workdays(s["start"], s["end"])
    s["first"], s["last"] = IDX[s["days"][0]], IDX[s["days"][-1]]
    s["cap"] = round(len(s["days"]) * FOCUS, 1)

MILESTONES = [
    (date(2026, 11, 13), "M0", "Kickoff"),
    (DEC1, "M1", "Dec 1 checkpoint demo"),
    (date(2026, 12, 11), "M2", "Leave and approvals feature-complete"),
    (date(2026, 12, 18), "M3", "Feature freeze, UAT starts"),
    (LAST_DAY, "M4", "Release candidate and handover"),
]


def I(i, mod, title, owner, est, sprint, tier="M", thin=False):
    return dict(id=i, mod=mod, title=title, owner=owner, est=est, sprint=sprint, tier=tier, thin=thin)


BACKLOG = [
    # Foundation
    I("WH-01", "Foundation", "Backend repo, CI, Docker Postgres, lint and test hooks", "JP", 1.0, 1, thin=True),
    I("WH-02", "Foundation", "Frontend repo (Bun, Vite), CI, generated API client", "JS", 1.0, 1, thin=True),
    I("WH-03", "Foundation", "Core database schema and migrations", "JP", 3.0, 1, thin=True),
    I("WH-04", "Foundation", "Microsoft Entra ID sign-in, sessions, role middleware", "JK", 3.0, 1, thin=True),
    I("WH-05", "Foundation", "App shell and design system, login screen", "JS", 3.0, 1, thin=True),
    I("WH-06", "Foundation", "Audit log write path", "JK", 1.0, 1, thin=True),
    I("WH-07", "Foundation", "Job worker skeleton: queue, schedules, failed-jobs list", "JP", 1.0, 3),
    # Organisation and projects
    I("WH-10", "Organisation", "Users, roles and teams admin (API and UI)", "JK", 1.5, 2, thin=True),
    I("WH-11", "Projects", "Projects and members (API and UI), client as text for now", "JK", 2.0, 2, thin=True),
    I("WH-12", "Projects", "Tasks v1: lists, create and edit, status", "JK", 1.4, 2, thin=True),
    I("WH-13", "Organisation", "Org settings, locations, holidays, work week", "JK", 1.5, 3),
    I("WH-14", "Projects", "Clients and work orders linked to projects", "JK", 1.0, 3),
    I("WH-15", "Projects", "Tasks v2: owners and teams, subtasks, comments, charge codes", "JK", 2.6, 3),
    # Time
    I("WH-20", "Time", "Time API: entries, week, rules, submit and lock", "JP", 3.0, 2, thin=True),
    I("WH-21", "Time", "Week grid UI: rows, day cells, totals, submit, send-back reasons", "JS", 3.0, 2, thin=True),
    # Approvals
    I("WH-30", "Approvals", "Approval engine v1: route, approve, send back with reason, history", "JP", 1.9, 2, thin=True),
    I("WH-31", "Approvals", "Approvals inbox v1: list, approve, send back", "JS", 1.5, 2, thin=True),
    I("WH-32", "Approvals", "Delegation, hourly escalation, pending-approval digest", "JP", 2.1, 3),
    I("WH-33", "Approvals", "Inbox depth: filters, bulk approve, approval timeline", "JP", 1.5, 3),
    # Leave
    I("WH-40", "Leave", "Leave types, balances, monthly accrual, admin UI", "JS", 3.0, 3),
    I("WH-41", "Leave", "Apply leave: balance preview, half-days, attachment, blackout check", "JS", 2.5, 3),
    I("WH-42", "Leave", "Leave approval: deduct balance, fill timesheet, cancel reversal", "JS", 2.0, 4),
    I("WH-43", "Leave", "Team calendar and monthly LWP export", "JS", 1.5, 4),
    # Payslips
    I("WH-50", "Payslips", "Payslip batch upload, ID matching preview, publish", "JK", 2.0, 4),
    I("WH-51", "Payslips", "Employee payslip view (masked, monthly tabs, download), documents", "JK", 1.5, 4),
    # Notifications
    I("WH-60", "Notifications", "Notification core: bell, grouping, per-event preferences", "JK", 1.5, 5),
    # Hardening
    I("WH-90", "Hardening", "Seed data (about 20 users, 2 locations, 3 teams) and four end-to-end journeys", "JP", 2.0, 4),
    I("WH-91", "Hardening", "Security, permission and audit-coverage sweep", "JP", 1.5, 4),
    I("WH-92", "Hardening", "UAT fixes, runbook and handover", "JK", 1.0, 5),
    I("WH-93", "Hardening", "Accessibility pass (WCAG 2.2 AA), UI polish, user guide", "JS", 1.5, 5),
    I("WH-94", "Hardening", "Bug-fix buffer, release checks and a basic load test", "JP", 1.5, 5),
    # Stretch: uses the buffer, in priority order
    I("WH-61", "Notifications", "Reminders: missing day, submit week, approver pending", "JP", 1.5, None, "S"),
    I("WH-22", "Time", "Edit-request flow for locked weeks", "JP", 1.0, None, "S"),
    I("WH-70", "Time", "Global timer in the top bar", "JP", 1.5, None, "S"),
    I("WH-71", "Time", "Calendar view: drag to log, resize to edit", "JS", 1.5, None, "S"),
    I("WH-72", "Leave", "Comp-off requests and credit", "JS", 1.0, None, "S"),
    I("WH-73", "Notifications", "Daily digest email and Teams messages", "JK", 2.0, None, "S"),
    I("WH-74", "Oversight", "Anomaly flags and manager dashboard", "JP", 4.0, None, "S"),
    I("WH-75", "Platform", "Saved views, project templates, command palette", "JK", 2.5, None, "S"),
    # Later: after Dec 25
    I("WH-80", "Suggestions", "Outlook calendar suggestions", "JP", 5.0, None, "C"),
    I("WH-81", "Suggestions", "Git commit and PR suggestions", "JK", 4.0, None, "C"),
    I("WH-82", "Suggestions", "Suggestions side panel and matching rules", "JS", 3.0, None, "C"),
    I("WH-83", "Oversight", "Weekly AI project status draft", "JP", 3.0, None, "C"),
    I("WH-84", "Oversight", "What-changed-since view", "JS", 2.0, None, "C"),
    I("WH-85", "Reports", "Reports: compliance, hours, leave, approvals, exports", "JS", 4.0, None, "C"),
    I("WH-86", "Migration", "Zoho import (dry run, then load)", "JK", 5.0, None, "C"),
    I("WH-87", "Client portal", "Client portal add-on (separate sign-in, shared reports, requests)", "JK", 10.0, None, "C"),
    I("WH-88", "Reports", "Scheduled report email and Excel export", "JP", 1.5, None, "C"),
]
BY_ID = {b["id"]: b for b in BACKLOG}
MODULES = ["Foundation", "Organisation", "Projects", "Time", "Approvals", "Leave", "Payslips", "Notifications", "Hardening"]


def schedule():
    """Place committed items per person in order; each takes est/FOCUS working days."""
    cursor = {k: 0.0 for k in TEAM}
    for p in TEAM:
        items = sorted([b for b in BACKLOG if b["owner"] == p and b["tier"] == "M"], key=lambda b: (b["sprint"], b["id"]))
        for b in items:
            sp = SPRINTS[b["sprint"] - 1]
            s = max(cursor[p], float(sp["first"]))
            e = s + b["est"] / FOCUS
            cursor[p] = e
            b["s_idx"], b["e_idx"] = s, e
            b["start"] = ALL_DAYS[min(int(s), len(ALL_DAYS) - 1)]
            b["end"] = ALL_DAYS[min(max(int(e - 1e-9), 0), len(ALL_DAYS) - 1)]
            b["overflow"] = e > sp["last"] + 1 + 1e-9
            b["late_for_dec1"] = b["thin"] and e > IDX[DEC1] + 1 + 1e-9


def sums():
    m = [b for b in BACKLOG if b["tier"] == "M"]
    s = [b for b in BACKLOG if b["tier"] == "S"]
    c = [b for b in BACKLOG if b["tier"] == "C"]
    return dict(m=sum(b["est"] for b in m), s=sum(b["est"] for b in s), c=sum(b["est"] for b in c),
                cap=round(len(ALL_DAYS) * FOCUS * 3, 1), thin=sum(b["est"] for b in m if b["thin"]),
                thin_cap=round(len([d for d in ALL_DAYS if d <= DEC1]) * FOCUS * 3, 1),
                days=len(ALL_DAYS), days_to_dec1=len([d for d in ALL_DAYS if d <= DEC1]))


def load_matrix():
    mx = {p: [0.0] * len(SPRINTS) for p in TEAM}
    for b in BACKLOG:
        if b["tier"] == "M":
            mx[b["owner"]][b["sprint"] - 1] += b["est"]
    return mx


schedule()

if __name__ == "__main__":
    S = sums()
    print("working days", S["days"], "to Dec 1", S["days_to_dec1"], [(s["n"], len(s["days"]), s["cap"]) for s in SPRINTS])
    print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in S.items()})
    mx = load_matrix()
    for p in TEAM:
        print(p, [round(x, 1) for x in mx[p]], "total", round(sum(mx[p]), 1), "capacity", round(len(ALL_DAYS) * FOCUS, 1))
    print("sprint capacity per person", [s["cap"] for s in SPRINTS])
    print("overflow or late for Dec 1:", [(b["id"], b["owner"], round(b["e_idx"], 1)) for b in BACKLOG if b["tier"] == "M" and (b["overflow"] or b["late_for_dec1"])])
