"""WorkHub Product Requirements Document in the Ampera template."""
import os
import render
import plan_data as P
from ampera_docx import AmperaDoc

H = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(H, "..", "assets", *p)
OUT = os.path.join(H, "..", "WorkHub_PRD_v0.1.docx")
S = P.sums()


def fn(pages):
    d = AmperaDoc("WorkHub Product\nRequirements Document", "AMP_WH_PRD_001", "0.1", "12-Nov-2026", "WorkHub (working name)",
                  cover_lines=["WORKHUB PRODUCT REQUIREMENTS DOCUMENT"])
    d.toc()
    d.doc_info([("Prepared By", "Jim, Janagan, Jayasree"), ("Reviewed By", "To be assigned"), ("Status", "Draft for review"),
                ("Audience", "Ampera leadership, delivery managers, HR, Finance, the WorkHub team"),
                ("Numbering", "Proposed ID. Compliance issues the final document number."),
                ("Related documents", "Sprint Plan (AMP_WH_SPL_001), Design Document (AMP_WH_DSN_001), Architecture (AMP_WH_ARC_001), FSD (AMP_WH_FSD_001), NFSD (AMP_WH_NFSD_001)")])

    d.h("2. Executive Summary", 1)
    d.p("Ampera runs timesheets in Zoho Projects, leave in Zoho People and payslips in Zoho Payroll. A walkthrough of our own portals "
        "shows the three apps disagree about the same day, hide who approved what, and send noisy notifications. WorkHub replaces them with one "
        "web tool built by Ampera: one calendar, one approval inbox, one place for time, leave and payslips.")
    d.tiles([(f"{S['m']:g} pd", "committed by Dec 24"), (f"{S['cap']:g} pd", "available, 3 people"), (f"{S['thin']:g} pd", "in the Dec 1 slice"),
             ("30", "working days to Dec 24")])
    d.callout("Decision needed",
              f"The full catalogue is about {S['m'] + S['s'] + S['c']:g} person-days; three people have {S['cap']:g}. This PRD commits "
              f"{S['m']:g} pd (91% of capacity) for Dec 24 and lists {S['s']:g} pd of stretch and {S['c']:g} pd for later. Dec 25 is a company holiday, "
              "so the effective deadline is Thursday, Dec 24.", color="A82080", fill="F8EAF4")
    d.figure(A("charts", "scope_capacity.png"), "Planned scope against capacity (person-days).", 6.2)

    d.h("3. Problem and Evidence", 1)
    d.h("3.1 Problem statement", 2)
    d.p("Employees, managers, HR and Finance at Ampera work across three Zoho apps that were bought separately. Staff re-enter the same day in "
        "different places, managers cannot see an approval trail without opening a hidden panel, and notifications are either too many or missing. "
        "The cost is late timesheets and manual reconciliation. It is not measured today (baseline: TBD, needs a Zoho admin export).")
    d.h("3.2 Evidence from our own portal (Employee login, 12 Nov 2026)", 2)
    d.table(["What we saw", "Where in Zoho", "Why it matters"],
            [["Projects shows 8 h logged on Tue 10 Nov; People shows the same day as Absent and its own Time Tracker is empty", "Projects > Time Logs; People > Home, Time Tracker", "Two time systems with no sync"],
             ["Leave approver, level and 'Acted in 4 days' sit behind a View button; the list shows only a tick", "People > Leave Requests > View", "No visible trail, no escalation"],
             ["99+ unread in Projects; one approval produced 5 identical notifications; preference is on or off per project", "Projects > bell", "Noise hides the notices that matter"],
             ["The Timesheets menu item opens 'Permission Denied' for an Employee", "Projects > left menu", "Access rules leak into the menu"],
             ["0 milestones and 0 issues across 16 projects; 16 standing charge codes carry the real work", "Projects > Projects, Organizational Tasks", "Time capture is the product"],
             ["Client and SOW numbers are kept as tags such as SOW-11101", "Projects > project tags", "No client or work-order record"]],
            [3.1, 1.9, 1.5], size=9.5)
    d.h("3.3 Evidence from the wider market", 2)
    d.p("About 90 sources (Zoho community forums, Zoho documentation, review sites and comparison articles) were read. Reddit and Quora could not be "
        "read, so community sentiment is under-sampled. Every theme we expected was confirmed by at least one source.")
    d.figure(A("charts", "pain_points.png"), "Top pain points by number of sources, coloured by whether we saw them in our own portal.", 6.2)

    d.h("4. Users and Roles", 1)
    d.table(["Role", "Who", "Job to be done"],
            [["Employee", "Consultants and engineers", "When Friday comes, I want to fill and submit my week in minutes, so I do not chase leave or project codes."],
             ["Manager", "Delivery and project managers", "When my team submits, I want to approve or send back with a reason in one place, so nothing waits for days."],
             ["HR", "HR operations", "When the month ends, I want leave balances, LWP days and payslips ready, so payroll is not delayed."],
             ["Finance", "Finance and billing", "When I close a period, I want hours by project and client, billable or not, so invoices are right."],
             ["Admin", "Platform administrators", "When someone joins or leaves, I want roles, teams and calendars set once, so access stays correct."],
             ["Client user", "Customer staff (optional add-on)", "When I want progress, I want a read-only view of my project, so I stop asking for status emails."]],
            [1.0, 1.8, 3.7], size=9.5)
    d.p("**Not for:** staff without an Ampera Microsoft 365 account (except client users), and mobile-only use. There is no mobile app in scope.")
    d.h("4.1 Permission matrix", 2)
    Y, N = "Yes", "-"
    d.table(["Action", "Employee", "Manager", "HR", "Finance", "Admin"],
            [["Log and submit own time", Y, Y, Y, Y, Y], ["Approve team time and leave", N, Y, N, N, N], ["Apply for leave", Y, Y, Y, Y, Y],
             ["Manage leave types, holidays, balances", N, N, Y, N, Y], ["Upload and publish payslips", N, N, Y, N, N],
             ["View own payslips", Y, Y, Y, Y, "Own only"], ["Create projects and tasks", N, Y, N, N, Y],
             ["Time reports across everyone", N, "Own team", N, Y, Y], ["Roles, integrations, audit log", N, N, N, N, Y]],
            [2.5, 0.8, 0.8, 0.8, 0.8, 0.8], size=9.5, align="lrrrrr".replace("r", "c"))
    d.note("Admins cannot read payslip contents unless they also hold the HR role. Suggestions and their evidence are visible only to their owner.")

    d.h("5. Proposed Solution", 1)
    d.p("One web application with a Python API and worker, one Postgres database, and Microsoft 365 sign-in. Approved leave and holidays fill the "
        "timesheet automatically, so the apps can never disagree. One approvals inbox covers timesheets and leave, with a visible trail, delegation "
        "and escalation. Payslips are uploaded as PDFs by HR and shown masked to each employee.")
    d.callout("Key hypothesis",
              "We believe one calendar and one approval inbox will cut reconciliation and late timesheets for Ampera's delivery staff and managers. "
              "We will know we are right when at least 95% of weeks are submitted on time and the median approval takes two working days or less "
              "(targets proposed; baselines TBD).")
    d.figure(A("charts", "feature_matrix.png"), "What comparable tools offer, from our research, against the WorkHub plan.", 6.2)
    d.h("5.1 What we are not building", 2)
    d.table(["Out of scope", "Why"],
            [["Mobile app", "Decision: web only"], ["Activity monitoring and screenshots", "Needs a desktop agent; legal and trust risk; decision: dropped"],
             ["Salary calculation", "HR uploads payslip PDFs; statutory rules are a separate project"],
             ["Rates, profitability, budgets, capacity planner", "Parked; not needed to replace Zoho"], ["Multi-company", "Ampera only for now; org settings keep the door open"]],
            [2.6, 3.9], size=9.5)

    d.h("6. Scope", 1)
    d.table(["Priority", "Capability", "Why"],
            [["Must (Dec 24)", "Sign-in, roles, org and people; clients, projects, tasks; week timesheet and submit; approval engine and inbox; leave types, balances, apply and approve with timesheet fill; payslip upload and view; notification core",
              "This replaces what Ampera uses in Zoho today"],
             ["Should (stretch)", "Timer, calendar view, copy last week, comp-off, reminders, digest and Teams, anomaly flags and manager dashboard, saved views and command palette", "Easier tracking; built only if buffer remains"],
             ["Could (later)", "Outlook and Git suggestions, weekly AI status, what-changed view, reports, Zoho import, client portal add-on", "Differentiators and selling points after the core works"],
             ["Won't", "Mobile app, monitoring, salary engine, multi-company, capacity planner", "Decisions above"]],
            [1.1, 3.9, 1.5], size=9.5)
    d.figure(A("charts", "module_stack.png"), "Effort by module and tier (person-days).", 6.0)
    d.h("6.1 MVP and the Dec 1 slice", 2)
    d.p(f"The Dec 1 slice is a thin vertical cut ({S['thin']:g} pd of {S['thin_cap']:g} pd available): a person signs in with Microsoft, sees projects and tasks, "
        "logs a week, submits it, and a manager approves or sends it back with a reason. Leave, payslips and notifications follow in Sprints 3 to 5.")

    d.h("7. Feature Summary", 1)
    feats = [("F1", "Sign-in and access", "Must", "S1", "Jayasree, Janagan", "Email and password sign-in (Microsoft Entra ID in version 2), five roles, access scoped by reporting line and project"),
             ("F2", "Organisation and people", "Must", "S2-S3", "Janagan", "Users, teams, locations, holidays, work week, April-March year"),
             ("F3", "Projects and tasks", "Must", "S2-S3", "Janagan", "Client, work order, project, task keys, charge codes, statuses, comments"),
             ("F4", "Time capture", "Must", "S2", "Jim, Jayasree", "Week grid, billable flag, notes, no future dates, submit and lock"),
             ("F5", "Approvals", "Must", "S2-S3", "Jim, Jayasree", "One engine and inbox, reasons, delegation, escalation, bulk approve"),
             ("F6", "Leave", "Must", "S3-S4", "Jayasree", "Types, balances, accrual, apply, approve, timesheet fill, team calendar, LWP export"),
             ("F7", "Payslips", "Must", "S4", "Janagan", "HR bulk upload, ID matching preview, masked employee view, download"),
             ("F8", "Notifications", "Must", "S5", "Janagan", "Grouped in-app bell and per-event preferences (reminders, digest in stretch)"),
             ("F9", "Oversight", "Should", "Stretch", "Jim", "Anomaly flags and manager dashboard"),
             ("F10", "Suggestions", "Could", "Later", "Jim, Janagan, Jayasree", "Outlook and Git drafts the employee accepts or rejects"),
             ("F11", "Client portal", "Could", "Later", "Janagan", "Optional add-on, separate sign-in, shared reports and requests"),
             ("F12", "Reports and import", "Could", "Later", "Jayasree, Janagan", "Compliance, hours and leave reports; Zoho import")]
    d.table(["ID", "Feature", "Priority", "Sprint", "Owner", "Summary"], [list(f) for f in feats], [0.4, 1.2, 0.65, 0.6, 1.0, 2.65], size=9)

    d.h("8. Success Metrics", 1)
    d.table(["Metric", "Target (proposed)", "Baseline", "How measured"],
            [["Weeks submitted on time", "95% or more", "TBD", "Submitted before the end of the last working day"],
             ["Median approval turnaround", "2 working days or less", "4 days (one request seen)", "Approval trail timestamps"],
             ["Days where leave and hours disagree", "0", "At least 1 seen", "Leave versus time-entry check"],
             ["Notifications per approval", "1 grouped", "5 seen", "Notification log"],
             ["Week view load, 95th percentile", "1.5 s or less", "Home exceeded 11 s", "Browser timing in the NFSD"]],
            [2.0, 1.5, 1.3, 1.7], size=9.5)

    d.h("9. Delivery Plan", 1)
    d.figure(A("charts", "roadmap.png"), "Sprints and milestones from Nov 13 to Dec 24.", 6.2)
    rows = [[str(s["n"]), s["name"], s["goal"], "pending", ["-", "with 1 tail", "with 2", "with 3", "-"][s["n"] - 1], ["-", "1", "2", "3", "4"][s["n"] - 1]] for s in P.SPRINTS]
    d.table(["#", "Phase", "What it delivers", "Status", "Parallel", "Depends"], rows, [0.3, 1.2, 3.3, 0.6, 0.6, 0.5], size=9)
    d.p("The detailed plan, owners and estimates are in the Sprint Plan (AMP_WH_SPL_001).")

    d.h("10. Technical Approach and Risks", 1)
    d.p("**Feasibility:** technology risk is low and schedule risk is medium. The stack is a React web app on Bun, a FastAPI API and worker on uv, "
        "Postgres, S3-compatible file storage and Microsoft 365 sign-in. The Architecture document has the detail.")
    d.table(["Risk", "Likelihood", "Mitigation"],
            [["Capacity is 91% committed", "High", "Cut line and stretch order in the Sprint Plan; weekly burn-up check"],
             ["Entra ID app registration or consent is delayed", "Medium", "Request registration on day 1; use a test tenant if needed"],
             ["Hosting target not decided", "Medium", "Decide by Nov 20; deployment work is sized for one environment"],
             ["Admin-side Zoho behaviour unknown", "Medium", "Ask a Zoho admin to confirm plan tiers and approval rules"],
             ["Payslip PDFs are sensitive", "Low", "Private storage, signed links, audit on every download"]],
            [2.4, 0.8, 3.3], size=9.5)

    d.h("11. Decisions Log", 1)
    d.table(["Decision", "Choice", "Alternatives", "Rationale"],
            [["Audience", "Ampera only", "Multi-company", "Faster; org settings keep multi-company possible"],
             ["Platform", "Web only", "Web plus mobile", "Capacity; mobile was the top Zoho complaint but is out of scope"],
             ["Monitoring", "None", "Activity capture, screenshots", "Needs a desktop agent; legal and trust risk"],
             ["Payslips", "HR uploads PDFs", "Generate from salary structure", "Statutory calculation is a separate project"],
             ["Stack", "Bun and React, FastAPI on uv, Postgres", "One Next.js app", "Python for rules and AI; one database"],
             ["Job queue", "Postgres table", "Redis", "One less service to run"],
             ["Client portal", "Optional add-on, off by default", "Core feature", "Core app never depends on it"],
             ["AI", "Suggests only, a person confirms", "Auto-submit", "Trust and accuracy"]],
            [1.0, 1.7, 1.5, 2.3], size=9)

    d.h("12. Open Questions", 1)
    d.table(["Question", "Owner", "Needed by"],
            [["Which hosting target (Azure assumed)?", "Team lead", "Nov 20"], ["Who registers the Entra ID app and grants consent?", "IT admin", "Nov 13"],
             ["Payslip file naming: can employee code be in the filename?", "HR", "Nov 27"], ["Holiday lists per location and any working Saturdays?", "HR", "Nov 27"],
             ["Approval chain beyond the direct manager?", "Delivery head", "Nov 27"], ["Zoho admin export for baseline metrics?", "Zoho admin", "Nov 20"],
             ["Final document numbers for the six documents?", "Compliance", "Before review"]],
            [3.7, 1.5, 1.3], size=9.5)

    d.h("13. Research Summary", 1)
    d.p("**Market:** agency tools (Productive, Teamwork, Float, Runn) and Odoo cover utilisation, planning and portals; Toggl, Clockify and Harvest make "
        "timesheets easy with timers, calendars and reminders; Plane and OpenProject cover tasks and basic time tracking. No vendor we found flags "
        "timesheet anomalies. **Technical:** monitoring needs a desktop agent and carries legal risk (a French regulator fined a company EUR 40,000 in 2024 "
        "for screenshots and idle tracking); India's DPDP rules apply in stages from 2027. Sources are in the research folder.")
    d.closing(14, "Jim, Janagan, Jayasree", "Initial draft of the WorkHub PRD from the Zoho research and the approved design.")
    return d


if __name__ == "__main__":
    pdf, n, missing = render.build(fn, OUT)
    print(pdf, n, "pages; headings without page:", missing)
    render.contact(pdf, os.path.join(H, "_ref", "prd.png"), 0, 12, 6, 44)
