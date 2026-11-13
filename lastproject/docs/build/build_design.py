"""WorkHub Design Document in the Ampera template (portrait, diagram-heavy)."""
import os
import render
from ampera_docx import AmperaDoc

H = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(H, "..", "assets", *p)
D = lambda n: A("diagrams", f"workhub-{n}.png")
OUT = os.path.join(H, "..", "WorkHub_Design_Document_v0.1.docx")


def fn(pages):
    d = AmperaDoc("WorkHub Design\nDocument", "AMP_WH_DSN_001", "0.1", "12-Nov-2026", "WorkHub (working name)", cover_lines=["WORKHUB DESIGN DOCUMENT"])
    d.toc()
    d.doc_info([("Prepared By", "Jim, Janagan, Jayasree"), ("Reviewed By", "To be assigned"), ("Status", "Draft for review"),
                ("Audience", "The WorkHub team, reviewers, future maintainers"),
                ("Related documents", "PRD (AMP_WH_PRD_001), FSD (AMP_WH_FSD_001), Architecture (AMP_WH_ARC_001), Sprint Plan (AMP_WH_SPL_001)")])

    d.h("2. Design Principles", 1)
    d.table(["Principle", "What it means in WorkHub", "Why (from our research)"],
            [["One day, one truth", "Approved leave and holidays write time entries, so timesheet, leave and calendar cannot disagree", "Zoho showed 8 h logged and 'Absent' for the same day"],
             ["Show the trail", "Approver, level, time taken and reason are visible in the list, not behind a button", "Leave approval trail hid behind a View button"],
             ["Quiet by default", "Group notices; one notice per approval; critical events always shown", "99+ unread, five identical notices"],
             ["Hide what you cannot open", "Menus show only what the role may use; the API enforces access", "Employees saw a Timesheets item that said Permission Denied"],
             ["AI suggests, people decide", "Drafts are never submitted automatically and are visible only to their owner", "Trust and privacy"],
             ["Fast first", "Pages under 1.5 s at the 95th percentile; keyboard-friendly", "Zoho Home took over 11 s"]],
            [1.4, 3.0, 2.1], size=9.5)

    d.h("3. Information Architecture", 1)
    d.p("WorkHub has five areas. Each person sees only the pages their role may use.", keep=True)
    d.figure(D("sitemap"), "Sitemap: five areas and their pages (* stretch or later).", 6.3)
    d.table(["Page", "Who", "Purpose", "Sprint"],
            [["Week timesheet", "Everyone", "Log, copy, submit a week; see sent-back reasons", "S2"], ["Leave", "Everyone", "Balances, apply, history, approval trail", "S3-S4"],
             ["Payslips", "Everyone", "Monthly tabs, masked amounts, download", "S4"], ["Approvals inbox", "Managers", "One queue for weeks and leave; approve or send back", "S2-S3"],
             ["Team calendar", "Managers, HR", "Who is out, tentative leave", "S4"], ["Clients, Projects, Tasks", "Managers, Admin", "Work structure and charge codes", "S2-S3"],
             ["Users and roles, Holidays, Leave types", "Admin, HR", "Organisation setup", "S2-S3"], ["Payslip batches", "HR", "Upload, match preview, publish", "S4"],
             ["Reports, Status reports", "Finance, Managers", "Hours, compliance, project status", "Later"]], [1.9, 1.2, 2.7, 0.7], size=9.5)

    d.h("4. Screen Design", 1)
    d.h("4.1 Week timesheet", 2)
    d.table(["Region", "Content", "Behaviour"],
            [["Header", "Week picker, total hours, status chip, Submit week", "Submit is disabled until the week has entries; the chip shows Draft, Submitted, Sent back or Approved"],
             ["Grid", "One row per task or charge code; one column per day; billable toggle per row; notes cell", "Leave and holiday cells are pre-filled and read-only; today's column is highlighted; day totals turn amber under and over the expected hours"],
             ["Row actions", "Add row, copy last week, pin row", "Copy last week brings rows and billable flags, not hours"],
             ["Sent-back banner", "Reason from the manager, pinned to the affected entries", "Editing an entry clears its pin; submitting again notifies the manager once"],
             ["Side panel (later)", "Suggestions from calendar and Git with evidence", "Accept, edit then accept, or reject; nothing is submitted for you"]],
            [1.2, 2.6, 2.7], size=9)
    d.h("4.2 Approvals inbox", 2)
    d.table(["Region", "Content", "Behaviour"],
            [["Filters", "Type (week, leave), person, age, flags", "Saved per user"],
             ["List", "Requester, period, hours or days, age, approver, status", "Rows older than the escalation limit show an amber age; select several to approve in bulk"],
             ["Detail drawer", "Entries or dates, notes, approval trail", "Approve, or Send back (reason required); the trail updates at once"],
             ["Delegation", "Banner when you hold delegated approvals", "Shows who delegated and until when"]], [1.2, 2.6, 2.7], size=9)
    d.h("4.3 Leave application", 2)
    d.table(["Region", "Content", "Behaviour"],
            [["Form", "Type, from and to, half-day per date, reason, attachment", "Reason required for unpaid leave; attachment required for long sick leave; blackout days block with a message"],
             ["Balance preview", "Balance now, this request, balance after", "Updates as dates change; warns if negative"],
             ["History", "Past requests with approver and days taken to decide", "Trail visible in the row, not behind a button"]], [1.2, 2.6, 2.7], size=9)
    d.h("4.4 Payslips", 2)
    d.table(["Region", "Content", "Behaviour"],
            [["Month tabs", "Latest months first, full history", "Amounts masked until clicked; each view and download is logged"],
             ["Documents", "Form 16 and letters", "Read-only; export available for exited employees through HR"]], [1.2, 2.6, 2.7], size=9)

    d.h("5. Domain Model", 1)
    d.p("Time is stored as integer minutes and dates as dates. Every table has id, created and updated stamps. Three diagrams split the model by area.", keep=True)
    d.figure(D("er-org"), "Organisation and work.", 6.4)
    d.figure(D("er-time"), "Time and approvals.", 6.4)
    d.figure(D("er-leave"), "Leave and payslips.", 6.4)
    d.table(["Rule", "Detail"],
            [["Approved leave writes entries", "Leave and holiday entries carry a source and are read-only in the grid"],
             ["Locked weeks", "An approved week is locked; reopening needs an approved edit request (stretch WH-22) or an admin override recorded in the audit log"],
             ["One target per entry", "Each time entry points to exactly one task or charge code"],
             ["Audit everywhere", "Every create, update and delete writes who, what, when, before and after"]], [2.0, 4.5], size=9.5)

    d.h("6. Lifecycles", 1)
    d.figure(D("week-lifecycle"), "Timesheet week lifecycle.", 6.3)
    d.table(["Leave status", "Meaning", "Next"],
            [["Applied", "Waiting for the approver; shown as tentative on the team calendar", "Approved, Rejected or Withdrawn"],
             ["Approved", "Balance deducted; leave entries written into the timesheet", "Cancelled (reverses both)"],
             ["Rejected", "Reason shown to the employee; nothing deducted", "-"],
             ["Withdrawn or Cancelled", "Balance and entries restored in one step", "-"]], [1.6, 3.4, 1.5], size=9.5)

    d.h("7. Key Flows", 1)
    d.figure(D("seq-week"), "Submit and approve a week.", 6.4)
    d.table(["Step", "What happens"],
            [["1-4", "The employee submits; the API checks the rules (no future dates, under 24 h a day, one target per entry) and answers"],
             ["5-6", "The API queues one notice; the worker tells the manager"], ["7-10", "The manager approves; the API locks the week, writes the audit event and answers"],
             ["11-12", "One grouped notice tells the employee the week is approved"]], [0.8, 5.7], size=9.5)
    d.figure(D("seq-leave"), "Leave approval fills the timesheet.", 6.4)
    d.table(["Step", "What happens"],
            [["1-3", "The employee applies; the leave module checks balance and blackout days and creates an approval"],
             ["4-6", "The manager is notified and approves; the engine tells the leave module"],
             ["7-9", "The balance is deducted and the time module writes leave entries into the week, all in one transaction"], ["10", "The employee is told"]], [0.8, 5.7], size=9.5)

    d.h("8. Module Design", 1)
    d.table(["Module", "Responsibility", "Depends on", "Raises"],
            [["people", "Users, roles, teams, locations, holidays, org settings", "-", "user changed"],
             ["projects", "Clients, work orders, projects, tasks, charge codes", "people", "task changed"],
             ["time", "Entries, weeks, rules, lock", "projects, people", "week submitted"],
             ["approvals", "One engine: routing, delegation, escalation, trail", "people", "approved, sent back"],
             ["leave", "Types, balances, accrual, requests, calendar", "approvals, time", "leave approved"],
             ["payslips", "Batches, matching, publish, documents", "people", "payslip published"],
             ["notifications", "Bell, grouping, preferences, schedules", "all (listens)", "-"],
             ["audit", "Immutable change log", "all (listens)", "-"],
             ["client_portal", "Optional add-on; separate identity", "projects, time", "request raised"]], [1.2, 3.0, 1.3, 1.0], size=9)

    d.h("9. Approval Engine", 1)
    d.table(["Rule", "Behaviour"],
            [["Routing", "To the requester's manager; to the delegate if the manager has an active delegation"],
             ["Send back", "Reason required; for a week, it returns to Draft with the reason pinned to entries"],
             ["Escalation", "Default 2 working days (set in org settings); then reassigned to the approver's manager and both are told"],
             ["Delegation", "From, to, start and end dates; pending items move when it starts"],
             ["Trail", "Every action is a step with who, what, when and comment; shown in the list"]], [1.4, 5.1], size=9.5)

    d.h("10. Time Rules", 1)
    d.table(["Rule", "Detail"],
            [["No future dates", "Entries cannot be dated after today (as in Zoho)"], ["Day limit", "No more than 24 h on a day"],
             ["One target", "A task or a charge code, never both"], ["Charge codes", "Only the teams a code is shared with can use it"],
             ["Week start", "Set in org settings (Monday or Sunday)"], ["Submit", "Week becomes Submitted and creates an approval; open anomaly flags are shown to the approver (stretch)"]],
            [1.6, 4.9], size=9.5)

    d.h("11. Suggestions (later)", 1)
    d.figure(D("suggestions"), "How suggested entries are made.", 6.4)
    d.table(["Order", "Matching rule"],
            [["1", "A project key in the meeting title or branch name"], ["2", "Attendee email domain mapped to a client"],
             ["3", "The user's own history for similar titles"], ["4", "No match: leave the target empty; the user picks"]], [0.8, 5.7], size=9.5)

    d.h("12. API and Error Conventions", 1)
    d.table(["Topic", "Convention"],
            [["Style", "JSON over HTTPS; resources by module; API schema published, web client types generated from it"],
             ["Errors", "One shape: code, message, field errors; the message is a plain sentence the screen shows"],
             ["Access", "Enforced in the API from the signed-in user's roles and reporting line; the menu only hides"],
             ["Writes", "Approval actions, balance changes and leave-to-timesheet fill each run in one transaction"],
             ["Jobs", "Retry three times with backoff, then appear in the admin failed-jobs list"]], [1.2, 5.3], size=9.5)

    d.h("13. Design Decisions", 1)
    for t, x in [("D1  Postgres as the job queue", "One less service to run for a three-person team. Upgrade to a broker only if volume demands it."),
                 ("D2  One approval engine", "Weeks, leave, comp-off and edit requests share routing, delegation, escalation and the trail. The inbox is one view."),
                 ("D3  Leave writes time entries", "The cheapest way to make timesheet, leave and calendar agree."),
                 ("D4  Client users are a separate identity", "A separate table and sign-in means a bug in role checks cannot expose employee data."),
                 ("D5  Integer minutes", "No rounding drift in totals or exports."),
                 ("D6  Payslips are uploaded PDFs", "Avoids statutory salary calculation; HR owns the content.")]:
        d.callout(t, x)

    d.h("14. Design Risks", 1)
    d.table(["Risk", "Mitigation"],
            [["Week grid is complex to build well", "Build the grid first (S2); copy last week and timer are stretch"],
             ["Approval engine rules grow", "Ship v1 rules in S2; delegation and escalation in S3 behind the same interface"],
             ["Masked payslip view is mistaken for security", "Real control is private storage, signed links and audit; masking only deters shoulder-surfing"]], [3.0, 3.5], size=9.5)
    d.closing(15, "Jim, Janagan, Jayasree", "Initial draft of the WorkHub design document.")
    return d


if __name__ == "__main__":
    pdf, n, missing = render.build(fn, OUT)
    print(pdf, n, "pages; headings without page:", missing)
    render.contact(pdf, os.path.join(H, "_ref", "design.png"), 0, 18, 6, 40)
