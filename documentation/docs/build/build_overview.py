"""WorkHub one-document overview in plain language (8 to 10 pages), Ampera template."""
import os
import render
import plan_data as P
from ampera_docx import AmperaDoc

H = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(H, "..", "assets", *p)
OUT = os.path.join(H, "..", "WorkHub_Overview_v0.1.docx")
S = P.sums()
mx = P.load_matrix()
CAP_EACH = len(P.ALL_DAYS) * P.FOCUS
pct = lambda a, b: f"{round(100 * a / b)}%"
fmt = lambda x: f"{x.day} {x.strftime('%b')}"

PHASES = {1: ("Set-up", "Everyone can sign in and work side by side; the database and the basic frame of the screens are ready."),
          2: ("First working version", "Sign in, see projects and tasks, fill in and submit a week; a manager approves it or sends it back."),
          3: ("Leave and smarter approvals", "Leave types, balances and applying for leave; hand approvals to a stand-in; bulk approve; clients and settings."),
          4: ("Payslips and leave in the timesheet", "HR uploads payslips; approved leave fills the timesheet; team calendar; a full test run."),
          5: ("Polish and handover", "Notifications, ease-of-use checks, fixes from user trials, handover notes. Ready on Dec 24.")}
LOOKS = {"JP": "Time and approval rules, the database, testing and security", "JK": "Sign-in, people and projects, payslips, notifications",
         "JS": "Screens and look, logging time, leave, ease of use"}


def fn(pages):
    d = AmperaDoc("WorkHub Product and\nDelivery Overview", "AMP_WH_SUM_001", "0.1", "12-Nov-2026", "WorkHub (working name)",
                  cover_lines=["WORKHUB PRODUCT AND DELIVERY OVERVIEW", "What we are building, how it works and when it is ready"])
    d.toc()
    d.doc_info([("Prepared By", "Jim, Janagan, Jayasree"), ("Status", "Draft for review"),
                ("Detail documents", "PRD, Sprint Plan, Design, Architecture, FSD, NFSD (AMP_WH_PRD_001 to AMP_WH_NFSD_001)")])

    d.h("2. Executive Summary", 1)
    d.p("WorkHub is one tool that replaces the three Zoho apps Ampera uses today: Projects (timesheets), People (leave) and Payroll (payslips). "
        "When we looked at our own accounts, the three apps disagreed about the same day, hid who approved what, and sent far too many notices. "
        "WorkHub gives people one calendar, one place to approve things, and one home for time, leave and payslips.")
    d.tiles([(pct(S["m"], S["cap"]), "of the time we have is already planned"), ("3 people", "full-time, 30 working days"),
             ("Dec 1", f"first working version; {pct(S['thin'], S['thin_cap'])} of the time before it is planned"), ("Dec 24", "the real deadline, because Dec 25 is a holiday")])
    d.callout("What fits and what does not",
              "We cannot build everything by Dec 24: the full wish list is about twice what three people can do. The plan builds the essentials first, "
              "which replace what Ampera uses in Zoho today. Bonus features come only if we are on track, and the rest waits until after launch.",
              color="A82080", fill="F8EAF4")

    d.h("3. Words Used Here", 1)
    d.table(["Word", "What it means"],
            [["Approval", "A manager says yes to a week or a leave request, or sends it back with a reason"],
             ["Charge code", "A label for time that is not on a client project, such as training or bench time"],
             ["Work order", "The client agreement (SOW) that pays for one or more projects"],
             ["Leave without pay", "Days off that are not paid; HR needs a monthly list for payroll"],
             ["First working version", "A small but real slice people can use, ready on Dec 1"],
             ["Bonus features", "Nice extras we build only if the essentials are on track"]], [1.7, 4.8], size=10)

    d.h("4. The Problem", 1)
    d.table(["What we saw in our own accounts (12 Nov 2026)", "Why it matters"],
            [["Projects showed 8 hours logged on Tue 10 Nov while People showed the same day as absent", "Two systems that do not talk to each other"],
             ["Who approved a leave request, and that it took 4 days, was hidden behind a button", "No clear record and no nudge when approval is slow"],
             ["More than 99 unread notices in Projects; one approval sent 5 identical notices", "The noise hides the notices that matter"],
             ["No milestones or issues in any of 16 projects; logging time does the real work", "So we build the timesheet first"]], [4.1, 2.4], size=9.5)
    d.figure(A("charts", "pain_points.png"), "What people complain about most, from about 90 sources. Dark pink: we saw it ourselves.", 4.8)

    d.h("5. Who Uses It", 1)
    d.table(["Role", "What they do here", "Can approve", "Sees payslips"],
            [["Employee", "Log and submit the week, apply for leave", "No", "Their own"], ["Manager", "Approve or send back; see who is away", "Yes, for their team", "Their own"],
             ["HR", "Set up leave; upload and publish payslips", "No", "Uploads and publishes"], ["Finance", "Hours and leave summaries", "No", "Their own"],
             ["Admin", "People, roles, connections, audit trail", "No", "Their own only"]], [0.9, 3.0, 1.4, 1.2], size=9.5)
    d.note("Admins cannot read other people's payslips unless they also work in HR. Suggestions and their evidence are private to the person they belong to.")

    d.h("6. What We Are Building", 1)
    F = [("Submit and lock a week", "Checks the week (no future dates, no day over 24 hours), sends it for approval and locks it once approved", "2", "Jim"),
         ("Approve or send back", "A manager approves, or sends back with a reason that shows on the exact entries", "2", "Jim"),
         ("Hand over and escalate approvals", "Approvals pass to a stand-in when someone is away, and to the next manager after two working days", "3", "Jim"),
         ("Bulk approve and approval trail", "Approve many at once; see who approved, when, and how long it took", "3", "Jim"),
         ("Reliable foundation", "The database, sample data, security checks and fix time before launch", "1, 4, 5", "Jim"),
         ("Microsoft sign-in and roles", "Staff sign in with their work account; five roles decide what each person sees", "1", "Janagan"),
         ("People, teams and settings", "Add people and teams; set holidays and the working week", "2-3", "Janagan"),
         ("Clients, projects and tasks", "Work orders, projects, tasks, and codes for non-project time such as training", "2-3", "Janagan"),
         ("Payslips", "HR uploads a month of payslips; each person sees only their own, hidden until clicked", "4", "Janagan"),
         ("Notifications and launch support", "One grouped notice instead of many, with personal settings; help during user trials", "5", "Janagan"),
         ("App look and feel", "The shared design, menus and sign-in screen everything else sits on", "1", "Jayasree"),
         ("Screens for time and approvals", "The weekly timesheet grid and the manager's approval inbox", "2", "Jayasree"),
         ("Leave types and balances", "Set up leave types, yearly balances and monthly build-up of days", "3", "Jayasree"),
         ("Applying for leave", "Apply with a balance preview; once approved, the leave fills the timesheet by itself", "3-4", "Jayasree"),
         ("Team calendar, leave summary, ease of use", "See who is away; monthly unpaid-leave list for payroll; checks that the app is easy to use", "4-5", "Jayasree")]
    d.table(["#", "Feature", "What it does", "Phase", "Owner"], [[str(i + 1), a, b, c, e] for i, (a, b, c, e) in enumerate(F)], [0.3, 1.75, 3.15, 0.55, 0.75], size=8.5)
    d.p("Each of us looks after five features. **Bonus if time allows:** a timer, a calendar view, reminders for missing days, warnings for odd timesheets, "
        "comp-off, saved views. **After launch:** suggestions from Outlook and Git, a weekly project summary, reports, importing from Zoho, a client portal. "
        "**Not building:** a mobile app, activity monitoring or screenshots, salary calculation, several companies in one system.", size=11, align="left")

    d.h("7. How It Fits Together", 1)
    d.figure(A("diagrams", "workhub-context.png"), "WorkHub sits between our people and the services it connects to: Microsoft 365, Git, an AI helper and, once, Zoho.", 5.3)
    d.bullets(["**What it is:** a web app people open in the browser, with their Microsoft work sign-in. (For the engineers: React, FastAPI and one Postgres database.)",
               "**One approval process** serves timesheets and leave. Approved leave fills the timesheet by itself, so the two can never disagree.",
               "**AI is optional and only suggests.** A person always confirms, and suggestions are private to the person they belong to.",
               "**Clients (optional add-on)** get their own sign-in and see only what is shared with them. It is off unless we turn it on."], size=11)

    d.h("8. How Well It Must Work", 1)
    d.table(["Area", "What we aim for", "Area", "What we aim for"],
            [["Speed", "Pages open in about a second and a half", "Always on", "Available almost all the time in working hours (99.5%)"],
             ["Safety net", "Backed up daily; at worst we lose one day of data and are back within four hours", "Sign-out", "Automatic after 60 minutes of inactivity"],
             ["Payslips", "Private files; download links stop working after five minutes", "Record keeping", "Every change and every payslip view is recorded for two years"],
             ["Easy to use", "Works with a keyboard and screen readers (WCAG 2.2 AA)", "Privacy", "No monitoring or screenshots; how long data is kept is still to be agreed with HR"],
             ["Quality checks", "Rules are tested automatically, plus four full walk-throughs", "Size", "Built for up to 500 people, tested with 200"]], [0.9, 2.4, 0.9, 2.3], size=9)

    d.h("9. The Plan", 1)
    d.figure(A("charts", "roadmap.png"), "Five phases from Nov 13 to Dec 24, with milestones.", 6.0)
    d.table(["Phase", "Dates", "What is ready at the end"],
            [[f"{s['n']}  {PHASES[s['n']][0]}", f"{fmt(s['start'])} to {fmt(s['end'])}", PHASES[s["n"]][1]] for s in P.SPRINTS], [1.7, 1.1, 3.7], size=9)
    d.table(["Person", "Looks after", "How full their plan is"],
            [[P.TEAM[p]["name"], LOOKS[p], f"{pct(sum(mx[p]), CAP_EACH)} of their time, nearly full" if sum(mx[p]) / CAP_EACH > 0.92 else f"{pct(sum(mx[p]), CAP_EACH)} of their time"] for p in P.TEAM],
            [1.0, 3.4, 2.1], size=9)
    d.p(f"**First working version (Dec 1):** sign in, see projects and tasks, fill in and submit a week, and a manager approves it or sends it back with a reason. "
        f"It uses about {pct(S['thin'], S['thin_cap'])} of the time before Dec 1, so there is almost no spare time. **If Phase 1 runs late,** we show it without the approval step. "
        "**What we drop first if we fall behind:** grouped notifications, the team calendar, bulk approve, linking clients to work orders, and extra ease-of-use polish, in that order.",
        size=11, align="left")

    d.h("10. Risks and Open Questions", 1)
    d.table(["Risk or question", "Chance", "What we do about it"],
            [[f"We have planned {pct(S['m'], S['cap'])} of our time; the first version has about {100 - round(100 * S['thin'] / S['thin_cap'])}% to spare", "High", "A list of what to drop first, a weekly progress check and a written fallback"],
             ["Setting up Microsoft sign-in for the app is delayed", "Medium", "Ask IT on Nov 13; use a test setup meanwhile"],
             ["Where WorkHub will run (hosting) is not decided", "Medium", "Team lead decides by Nov 20"],
             ["We have only seen Zoho as an ordinary employee, not as an admin", "Medium", "Ask a Zoho admin to confirm plans and approval rules"],
             ["Payslip file names, holiday lists, leave rules and official document numbers", "Open", "HR and Compliance"]], [3.3, 0.8, 2.4], size=9)
    d.closing(11, "Jim, Janagan, Jayasree", "Plain-language overview of the WorkHub product and delivery plan.")
    return d


if __name__ == "__main__":
    pdf, n, missing = render.build(fn, OUT)
    print(pdf, n, "pages; headings without page:", missing)
    render.contact(pdf, os.path.join(H, "_ref", "overview.png"), 0, 12, 6, 44)
