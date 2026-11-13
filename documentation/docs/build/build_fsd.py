"""WorkHub Functional Specification Document in the Ampera template."""
import os
import render
import charts
from ampera_docx import AmperaDoc

H = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(H, "..", "assets", *p)
D = lambda n: A("diagrams", f"workhub-{n}.png")
OUT = os.path.join(H, "..", "WorkHub_FSD_v0.1.docx")
M, S_, C_ = "Must", "Should", "Could"

# (code, title, actors, rules, acceptance, [(text, priority, sprint, item, source)])
MODULES = [
    ("ACC", "Sign-in and access", "All users", ["An email maps to one user; deactivating a user keeps history.", "Access is denied unless a rule allows it."],
     ["Given an Employee, when they open a manager-only address, then they see not found and the attempt is logged.", "Given an exited user, when they sign in, then access is denied."],
     [("Sign in with Microsoft Entra ID and match the work email to an active user", M, "S1", "WH-04", "Decision: Microsoft 365 is the identity provider"),
      ("Five roles (Employee, Manager, HR, Finance, Admin); a person may hold several", M, "S1", "WH-04", "PRD permission matrix"),
      ("The API enforces access by role, reporting line and project membership", M, "S1", "WH-04", "Zoho: blocked page behind a visible menu item"),
      ("Menus show only pages the role can open", M, "S1", "WH-05", "Zoho: Timesheets menu item showed Permission Denied"),
      ("Sessions end after 60 minutes idle", M, "S1", "WH-04", "NFSD SEC-02"),
      ("Exited users cannot sign in; their history and payslips are kept", M, "S2", "WH-10", "Design D6")]),
    ("ORG", "Organisation and people", "Admin, HR", ["One manager per user; the manager chain must not loop.", "The leave year runs April to March."],
     ["Given a manager chain A to B to A, when an admin saves it, then the save is refused with a clear message."],
     [("Create and edit users: employee code, designation, location, manager, join and exit dates", M, "S2", "WH-10", "Zoho People profile"),
      ("Teams and membership", M, "S2", "WH-10", "Zoho tasks assigned to teams"),
      ("Locations, each with its own holiday list", M, "S3", "WH-13", "People holiday calendar"),
      ("Org settings: work week, week start, expected hours per day, financial year", M, "S3", "WH-13", "Zoho work week set to Sun-Thu"),
      ("Audit log viewer for admins", S_, "Later", "-", "Zoho: audit log owner-only")]),
    ("PRJ", "Projects and tasks", "Managers, Admin", ["Project keys are unique; task keys are the project prefix plus a number.", "A charge code is available only to teams it is shared with."],
     ["Given a charge code shared with Team X only, when a member of Team Y logs time, then the code is not offered."],
     [("Projects with unique key, group, status, visibility and manager", M, "S2", "WH-11", "Zoho project list"),
      ("Project members with a project role", M, "S2", "WH-11", "Zoho members"),
      ("Clients and work orders linked to projects", M, "S3", "WH-14", "Zoho: SOW numbers kept as tags"),
      ("Tasks with task lists, status, priority and dates", M, "S2", "WH-12", "Zoho tasks"),
      ("Task owners or teams, subtasks and comments", M, "S3", "WH-15", "Zoho task tabs"),
      ("Charge codes for non-project time (Bench, Training, Proposal)", M, "S3", "WH-15", "Zoho Organizational Tasks project"),
      ("Saved views, project templates, command palette", S_, "Stretch", "WH-75", "Plane, Linear")]),
    ("TIM", "Time capture", "Employees, Managers", ["Entries cannot be future-dated or exceed 24 hours a day.", "An entry has exactly one task or charge code.", "Approved weeks are locked."],
     ["Given tomorrow's date, when an employee logs time, then the system refuses with a clear message.", "Given approved leave on Tuesday, when the week opens, then Tuesday shows leave and cannot be edited."],
     [("Week grid: a row per task or charge code, a column per day", M, "S2", "WH-21", "Zoho Time Logs grid"),
      ("Billable flag per row; notes per entry", M, "S2", "WH-21", "Zoho billing type"),
      ("Reject future dates, over 24 hours a day, entries with no or two targets", M, "S2", "WH-20", "Zoho: no future dates"),
      ("Submitting a week creates an approval and makes the week read-only", M, "S2", "WH-20", "Design D2"),
      ("Approved weeks are locked", M, "S2", "WH-20", "Clockify lock dates"),
      ("Leave and holiday cells are pre-filled and read-only", M, "S4", "WH-42", "Zoho: Absent versus 8 h conflict"),
      ("Copy last week and pinned rows", S_, "Stretch", "WH-75", "Harvest, Clockify"),
      ("Global timer in the top bar", S_, "Stretch", "WH-70", "Odoo"),
      ("Calendar view: drag to log, resize to edit", S_, "Stretch", "WH-71", "OpenProject")]),
    ("APR", "Approvals", "Managers, Employees", ["Send back needs a reason.", "Escalation limit is 2 working days unless org settings say otherwise."],
     ["Given a week pending for 3 working days, when the hourly check runs, then it moves to the manager's manager and both are told.", "Given a sent-back week, when the employee opens it, then the reason shows on the affected entries."],
     [("One engine routes weeks and leave to the requester's manager", M, "S2", "WH-30", "Design D2"),
      ("Approve, or send back with a required reason", M, "S2", "WH-30", "Zoho: rejection gives no reason"),
      ("Inbox lists pending items with age", M, "S2", "WH-31", "Odoo, Clockify"),
      ("Reason pinned to the affected entries", M, "S2", "WH-21", "Zoho forums: rejection notification"),
      ("Trail shows approver, level, time taken and comment in the list", M, "S3", "WH-33", "Zoho: trail behind a View button"),
      ("Delegation with dates; pending items move", M, "S3", "WH-32", "Zoho forums: delegation"),
      ("Escalate after 2 working days", M, "S3", "WH-32", "Zoho: 4-day wait, no escalation"),
      ("Bulk approve and filters", M, "S3", "WH-33", "Zoho forums: no bulk approve")]),
    ("LEV", "Leave", "Employees, Managers, HR", ["Approve deducts the balance and writes timesheet entries in one transaction.", "Cancelling reverses both together."],
     ["Given 1.5 days balance and a 2-day request, when applying, then the preview shows -0.5 and warns.", "Given approved leave that is cancelled, when confirmed, then balance and entries are restored together."],
     [("Leave types with paid flag, accrual and carry-forward", M, "S3", "WH-40", "People leave types"),
      ("Balances per user, type and leave year", M, "S3", "WH-40", "People leave summary"),
      ("Apply with half-day per date, reason and attachment", M, "S3", "WH-41", "People apply form (no attachment)"),
      ("Balance preview before submitting", M, "S3", "WH-41", "Design D5"),
      ("Block leave on blackout days", M, "S3", "WH-41", "Odoo stress days"),
      ("Approve: deduct balance and fill the timesheet", M, "S4", "WH-42", "Zoho: apps disagree"),
      ("Cancel or withdraw reverses balance and entries", M, "S4", "WH-42", "Design D3"),
      ("Team calendar with tentative leave; monthly LWP export", M, "S4", "WH-43", "Float, payroll need"),
      ("Comp-off request and credit", S_, "Stretch", "WH-72", "People comp-off")]),
    ("PAY", "Payslips", "HR, Employees", ["Files are matched by employee code in the file name.", "Admins cannot read payslips unless they also hold HR."],
     ["Given a batch with one unmatched file, when HR previews, then the file is listed and the batch cannot be published until it is fixed."],
     [("HR uploads a ZIP or several PDFs for a month", M, "S4", "WH-50", "Decision: upload PDFs"),
      ("Match by employee code; preview lists matched, unmatched and duplicate files", M, "S4", "WH-50", "Design"),
      ("Publishing notifies each employee", M, "S4", "WH-50", "Zoho Payroll"),
      ("Employee view: monthly tabs, masked amounts, download", M, "S4", "WH-51", "Zoho Payroll portal"),
      ("Form 16 and letters as documents", M, "S4", "WH-51", "Zoho Payroll Documents"),
      ("Every view and download is audited", M, "S4", "WH-51", "NFSD SEC-05"),
      ("Download all and access after exit", C_, "Later", "-", "Zoho forums: payslips after exit")]),
    ("NOT", "Notifications", "All users", ["Critical events (approval requested, approved, sent back, payslip published) are always shown in the app."],
     ["Given five entries approved together, when the employee opens the bell, then one notice reads '5 entries approved'."],
     [("In-app bell with grouped notices", M, "S5", "WH-60", "Zoho: five identical notices"),
      ("Per-event preferences", M, "S5", "WH-60", "Zoho: on or off per project only"),
      ("Reminders for missing days and for submitting the week", S_, "Stretch", "WH-61", "Odoo, Clockify"),
      ("Daily digest and Teams messages", S_, "Stretch", "WH-73", "Toggl, Harvest")]),
    ("OVS", "Oversight", "Managers", [], [],
     [("Anomaly flags: missing day, week over 50 hours, hours on leave, unassigned code, copied notes, sharp drop", S_, "Stretch", "WH-74", "No vendor ships this"),
      ("Manager dashboard: submission rate, missing days, pending items, who is out", S_, "Stretch", "WH-74", "Odoo, Teamwork"),
      ("Weekly AI project status draft that the manager edits", C_, "Later", "WH-83", "Asana, ClickUp"),
      ("What-changed-since view", C_, "Later", "WH-84", "OpenProject baseline")]),
    ("SUG", "Suggestions", "Employees", [], [],
     [("Outlook meetings become suggestions", C_, "Later", "WH-80", "Tempo, ClickTime"),
      ("Git commits and pull requests become suggestions", C_, "Later", "WH-81", "Tempo"),
      ("Side panel: accept, edit then accept, reject; visible only to the owner", C_, "Later", "WH-82", "Privacy decision")]),
    ("CLI", "Client portal (add-on)", "Client users, Managers", [], [],
     [("Off by default; core never depends on it", C_, "Later", "WH-87", "Decision"),
      ("Separate identity and email-link sign-in", C_, "Later", "WH-87", "Design D4"),
      ("Read-only progress, approved-hours summary and shared reports", C_, "Later", "WH-87", "Odoo portal"),
      ("Client requests become tasks; ratings on chosen stages", C_, "Later", "WH-87", "Odoo ratings")]),
    ("REP", "Reports and migration", "Finance, Managers, Admin", [], [],
     [("Compliance, hours, leave and approval reports", C_, "Later", "WH-85", "Zoho: shallow reports"),
      ("CSV and Excel export; scheduled email", C_, "Later", "WH-88", "Productive"),
      ("Zoho import with a dry run first", C_, "Later", "WH-86", "Migration need")])]


def fn(pages):
    d = AmperaDoc("WorkHub Functional\nSpecification Document", "AMP_WH_FSD_001", "0.1", "12-Nov-2026", "WorkHub (working name)",
                  cover_lines=["WORKHUB FUNCTIONAL SPECIFICATION DOCUMENT"])
    d.toc()
    d.doc_info([("Prepared By", "Jim, Janagan, Jayasree"), ("Reviewed By", "To be assigned"), ("Status", "Draft for review"),
                ("Audience", "Developers, testers, reviewers, product owner"),
                ("Companion", "Non-Functional Specification Document (AMP_WH_NFSD_001)")])

    d.h("2. Introduction", 1)
    d.h("2.1 Purpose of the document", 2)
    d.p("This document says what WorkHub does, for each module, in numbered requirements that can be tested. It is the companion to the NFSD, which says how well the system must do it.")
    d.h("2.2 Project scope", 2)
    d.p("WorkHub replaces Zoho Projects (timesheets), Zoho People (leave) and Zoho Payroll (payslips) for Ampera. Web only; no mobile app and no activity monitoring.")
    d.h("2.3 Related documents", 2)
    d.table(["Document", "Reference"], [["Product Requirements", "AMP_WH_PRD_001"], ["Sprint Plan", "AMP_WH_SPL_001"], ["Design Document", "AMP_WH_DSN_001"],
                                         ["Architecture Document", "AMP_WH_ARC_001"], ["NFSD", "AMP_WH_NFSD_001"]], [3.0, 3.5], size=10)
    d.h("2.4 Terms and acronyms", 2)
    d.table(["Term", "Definition"],
            [["Charge code", "A code for time not tied to a project, such as Bench or Training"], ["Work order", "A client agreement (SOW) that funds one or more projects"],
             ["LWP", "Leave without pay"], ["Week", "A user's timesheet for seven days, starting on the day set in org settings"],
             ["Slice", "The Dec 1 thin vertical cut of the product"]], [1.5, 5.0], size=10)
    d.h("2.5 Risks and assumptions", 2)
    d.bullets(["Assumed: Ampera staff have Microsoft 365 accounts; the Entra ID app registration is granted.", "Assumed: payslip PDF file names carry the employee code.",
               "Assumed: one approval level (the direct manager) for v1.", "Risk: scope is larger than capacity; see the Sprint Plan cut line."], size=11)

    d.h("3. System Overview", 1)
    d.h("3.1 Context, sitemap and lifecycle", 2)
    d.figure(D("context"), "System context.", 6.3)
    d.figure(D("sitemap"), "Sitemap (* stretch or later).", 6.0)
    d.figure(D("week-lifecycle"), "Timesheet week lifecycle.", 6.0)
    d.h("3.2 System actors", 2)
    d.table(["Role", "Typical use", "Frequency"],
            [["Employee", "Log and submit a week, apply for leave, view payslips", "Daily to weekly"], ["Manager", "Approve or send back, view team calendar", "Daily"],
             ["HR", "Leave setup, balances, payslip batches", "Weekly to monthly"], ["Finance", "Reports and the LWP export", "Monthly"],
             ["Admin", "Users, roles, integrations, audit", "Occasionally"], ["Client user (add-on)", "Read shared progress and reports", "Weekly"]], [1.5, 3.7, 1.3], size=10)
    d.h("3.3 Dependencies", 2)
    d.table(["Dependency", "Needed for"], [["Microsoft Entra ID app registration", "Sign-in (S1)"], ["Hosting target and managed Postgres", "Shared dev and production (S3)"],
                                            ["HR holiday lists and leave policy", "Org settings and leave types (S3)"], ["Payslip PDF naming rule", "Payslip upload (S4)"]], [3.5, 3.0], size=10)

    d.h("4. Functional Specifications", 1)
    counts = {}
    for n, (code, title, actors, rules, acc, reqs) in enumerate(MODULES, 1):
        d.h(f"4.{n} {title}", 2)
        d.p(f"**Actors:** {actors}.   **Requirement IDs:** FR-{code}-nn.", align="left", keep=True)
        rows = []
        for k, (text, pr, sp, wh, src) in enumerate(reqs, 1):
            rows.append([f"FR-{code}-{k:02d}", text, pr, sp, wh, src])
            counts.setdefault(title, {M: 0, S_: 0, C_: 0})[pr] += 1
        d.table(["ID", "Requirement", "Priority", "Sprint", "Item", "Source"], rows, [0.8, 2.75, 0.6, 0.55, 0.55, 1.25], size=8.5)
        if rules:
            d.p("**Business rules**", align="left", keep=True, after=2)
            d.bullets(rules, size=10.5)
        if acc:
            d.p("**Acceptance criteria**", align="left", keep=True, after=2)
            d.bullets(acc, size=10.5)

    d.h("5. System Configurations", 1)
    d.table(["Setting", "Default", "Who changes it"],
            [["Work week days and week start", "Monday to Friday, Monday", "Admin"], ["Expected hours per day", "8 (480 minutes)", "Admin"], ["Financial and leave year", "April to March", "HR"],
             ["Approval escalation limit", "2 working days", "Admin"], ["Anomaly week limit (stretch)", "50 hours", "Admin"], ["Client portal", "Off", "Admin"],
             ["Holiday list per location", "None until added", "HR"]], [2.6, 2.2, 1.7], size=10)

    d.h("6. Reporting Requirements", 1)
    d.table(["Report", "Audience", "Sprint"],
            [["Monthly LWP and leave taken per employee (export)", "HR, Finance", "S4"], ["Timesheet compliance", "Managers, Finance", "Later"],
             ["Hours by project, client, charge code, person; billable split", "Finance, Managers", "Later"], ["Approval turnaround", "Managers", "Later"]], [3.8, 1.7, 1.0], size=10)

    d.h("7. Integration Requirements", 1)
    d.table(["Integration", "Requirement"],
            [["Microsoft Entra ID", "Sign-in with OIDC; match on work email"], ["Outlook calendar (later)", "Read-only, per-user consent"], ["Teams (stretch)", "Approval and reminder messages"],
             ["GitHub and GitLab (later)", "OAuth per user; repositories mapped to projects"], ["LLM service (later)", "Optional text help only; rules decide first"]], [2.2, 4.3], size=10)
    d.h("7.1 Exception handling", 2)
    d.p("An integration failure never stops a user logging time. The user sees a reconnect notice; the job retries three times with backoff and then appears in the admin failed-jobs list.")

    d.h("8. Data Migration", 1)
    d.p("A one-off Zoho import (later, WH-86) reads projects, tasks, time logs, users, leave types and balances through the Zoho Projects connector or CSV. It runs as a dry run first, prints counts and mismatches, and is safe to re-run because it is keyed on Zoho IDs. Until then, the seed script loads realistic sample data.")

    d.h("9. Non-Functional Requirements", 1)
    d.p("Performance, security, privacy, accessibility and operations are specified in the NFSD (AMP_WH_NFSD_001).")
    d.h("10. Open Issues", 1)
    d.table(["Issue", "Owner"], [["Hosting target", "Team lead"], ["Entra ID registration owner", "IT admin"], ["Leave policy details (accrual, carry-forward caps)", "HR"],
                                  ["Final document numbers", "Compliance"]], [4.5, 2.0], size=10)

    d.h("11. Requirement Summary", 1)
    cats = list(counts)
    p = charts.stacked("fsd_requirements", cats, [("Must", [counts[c][M] for c in cats]), ("Should", [counts[c][S_] for c in cats]), ("Could", [counts[c][C_] for c in cats])],
                       [charts.NAVY, charts.LAV, charts.LGREY], "Requirements", figsize=(7.2, 4.0))
    d.figure(p, f"Requirements by module and priority ({sum(sum(v.values()) for v in counts.values())} in total).", 6.0)
    d.closing(12, "Jim, Janagan, Jayasree", "Initial draft of the WorkHub functional specification.")
    return d


if __name__ == "__main__":
    pdf, n, missing = render.build(fn, OUT)
    print(pdf, n, "pages; headings without page:", missing)
    render.contact(pdf, os.path.join(H, "_ref", "fsd.png"), 0, 18, 6, 40)
