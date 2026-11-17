"""WorkHub Sprint Plan in the Ampera template (landscape, chart-heavy)."""
import os
import render
import plan_data as P
import charts
from ampera_docx import AmperaDoc

H = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(H, "..", "assets", *p)
OUT = os.path.join(H, "..", "WorkHub_Sprint_Plan_v0.1.docx")
S = P.sums()
NM = lambda k: P.TEAM[k]["name"]
fmt = lambda dt: f"{dt.day} {dt.strftime('%b')}"
committed = [b for b in P.BACKLOG if b["tier"] == "M"]

EXIT = {1: "All three can sign in (email and password; Microsoft comes in version 2), run the stack locally, and push through CI. Database migrations apply cleanly.",
        2: "Demo on Dec 1: sign in, see projects and tasks, log and submit a week, manager approves or sends back with a reason.",
        3: "Leave types and balances work; leave can be applied for; delegation, escalation and bulk approve work; org settings and work orders exist.",
        4: "Payslips upload, match and publish; leave approval fills the timesheet; team calendar; end-to-end tests pass. Feature freeze Dec 18.",
        5: "Release candidate on Dec 24: accessibility pass done, UAT fixes closed, runbook and handover written."}
MITIGATION = {"R1": "Cut line (section 10); weekly burn-up check; stretch work starts only when committed work is on track",
              "R2": "Raise the app registration request on Nov 13; fall back to a test tenant",
              "R3": "Decide hosting by Nov 20; size deployment for one environment",
              "R4": "Pair review on every pull request so a second person knows each module",
              "R5": "Stretch and later lists are frozen; new asks go to the Later list",
              "R6": "Ask a Zoho admin to confirm approval rules and plan tiers by Nov 20",
              "R7": "Private storage, signed links, audit on every payslip view; confirm handling rules with HR",
              "R8": "If Sprint 1 slips by more than 1 pd, drop approvals from the Dec 1 demo (section 5)"}
OWNER_R = {"R1": "Jim", "R2": "Janagan", "R3": "Jim", "R4": "All", "R5": "Jim", "R6": "Jayasree", "R7": "Janagan", "R8": "Jim"}
LVL = {1: "Low", 2: "Medium", 3: "High"}


def fn(pages):
    d = AmperaDoc("WorkHub Sprint Plan", "AMP_WH_SPL_001", "0.1", "12-Nov-2026", "WorkHub (working name)", landscape=True,
                  cover_lines=["WORKHUB SPRINT PLAN"])
    d.toc()
    d.doc_info([("Prepared By", "Jim, Janagan, Jayasree"), ("Reviewed By", "To be assigned"), ("Status", "Draft for review"),
                ("Plan window", "Fri 13 Nov to Thu 24 Dec 2026 (30 working days; Dec 25 is a company holiday)"),
                ("Capacity rule", "3 people, full-time, 70% of each day is focused build time (meetings, reviews and support take the rest)"),
                ("Related documents", "PRD (AMP_WH_PRD_001), FSD (AMP_WH_FSD_001), Architecture (AMP_WH_ARC_001)")])

    d.h("2. Plan on a Page", 1)
    d.tiles([(f"{S['cap']:g} pd", "capacity: 3 people, 30 days"), (f"{S['m']:g} pd", "committed, 91% of capacity"),
             (f"{S['thin']:g} pd", f"Dec 1 slice of {S['thin_cap']:g} available"), (f"{S['s']:g} pd", "stretch, only if on track"),
             (f"{S['c']:g} pd", "later, after Dec 25")])
    d.callout("Three things to know",
              "1) Dec 25 is a holiday, so the real deadline is Thursday Dec 24.  2) The full catalogue is about 110 pd against 63 available, so this plan "
              "commits the Zoho replacement core and lists the rest.  3) The Dec 1 slice uses 96% of its capacity, so it has a written fallback.",
              color="A82080", fill="F8EAF4")
    d.figure(A("charts", "roadmap.png"), "Sprints and milestones, Nov 13 to Dec 24.", 8.2)
    d.figure(A("charts", "scope_capacity.png"), "Planned scope against capacity (person-days).", 7.0)

    d.h("3. Team and Ownership", 1)
    d.p("Each person owns whole modules end to end (screens, API and tests). Week 1 foundations are split evenly so nobody waits on another layer.", align="left", keep=True)
    mx = P.load_matrix()
    rows = []
    for p in P.TEAM:
        mods = sorted({b["mod"] for b in committed if b["owner"] == p}, key=P.MODULES.index)
        rows.append([NM(p), P.TEAM[p]["lane"], P.TEAM[p]["focus"], ", ".join(mods), f"{sum(mx[p]):.1f}",
                     f"{sum(b['est'] for b in committed if b['owner'] == p and b['thin']):.1f}"])
    d.table(["Person", "Lane", "Focus", "Modules owned (committed)", "Committed pd", "Dec 1 pd"], rows, [0.9, 1.3, 2.4, 2.6, 0.9, 0.9], size=10)
    d.note("Roles are assigned by module, not by job title. Swap modules if strengths differ; the load per person stays within 1 pd of the others.")

    d.h("4. Sprint Overview", 1)
    mxs = [sum(mx[p][i] for p in P.TEAM) for i in range(5)]
    d.table(["Sprint", "Dates", "Days", "Capacity pd", "Committed pd", "Goal", "Exit criteria"],
            [[f"S{s['n']} {s['name']}", f"{fmt(s['start'])} to {fmt(s['end'])}", str(len(s["days"])), f"{s['cap'] * 3:.1f}", f"{mxs[s['n'] - 1]:.1f}", s["goal"], EXIT[s["n"]]] for s in P.SPRINTS],
            [1.0, 0.95, 0.4, 0.6, 0.7, 2.6, 2.75], size=9)

    d.h("5. The Dec 1 Slice", 1)
    d.p(f"The slice is {S['thin']:g} pd of {S['thin_cap']:g} pd available over 13 working days. It is a thin vertical cut so there is something real to show.", align="left", keep=True)
    thin = sorted([b for b in committed if b["thin"]], key=lambda b: (b["sprint"], b["id"]))
    d.table(["ID", "Item", "Owner", "pd", "Sprint", "Planned finish"],
            [[b["id"], b["title"], NM(b["owner"]), f"{b['est']:g}", f"S{b['sprint']}", fmt(b["end"])] for b in thin], [0.7, 5.0, 1.0, 0.5, 0.7, 1.1], size=9.5)
    d.h("5.1 Demo script for Dec 1", 2)
    d.bullets(["Sign in with email and password and land on the app shell.", "An admin adds a user and a project member; the project and its tasks appear.",
               "The employee opens this week, logs hours against two tasks and one charge code, and submits.", "The manager opens the approvals inbox and sends one week back with a reason.",
               "The employee sees the reason on the entry, fixes it and resubmits; the manager approves and the week locks."], numbered=True)
    d.callout("Fallback if Sprint 1 slips by more than 1 pd",
              "Drop WH-30 and WH-31 (approval engine and inbox, 3.4 pd) from the Dec 1 demo and show sign-in, projects, tasks and timesheet submit. "
              "Approvals move to Dec 2 to Dec 4 at the front of Sprint 3.", color="002060", fill="EEF2FA")
    d.figure(A("charts", "burnup.png"), "Planned cumulative burn-up of committed work against capacity.", 6.8)

    d.h("6. Committed Backlog by Sprint", 1)
    d.table(["ID", "Module", "Item", "Owner", "pd", "Sprint", "Start", "End", "Dec 1"],
            [[b["id"], b["mod"], b["title"], NM(b["owner"]), f"{b['est']:g}", f"S{b['sprint']}", fmt(b["start"]), fmt(b["end"]), "Yes" if b["thin"] else ""]
             for b in sorted(committed, key=lambda b: (b["sprint"], b["s_idx"], b["id"]))],
            [0.65, 1.0, 3.6, 0.8, 0.4, 0.5, 0.65, 0.65, 0.45], size=8.5)

    d.h("7. Timeline", 1)
    d.figure(A("charts", "gantt.png"), "Committed work by person. Outlined bars are in the Dec 1 slice; dashed lines are milestones.", 7.7)

    d.h("8. Capacity and Load", 1)
    d.figure(A("charts", "sprint_capacity.png"), "Capacity against committed work per sprint (all three people).", 6.6)
    d.figure(A("charts", "util_heatmap.png"), "Load against capacity per person and sprint (person-days and percent).", 7.4)
    d.p("Sprints 2 and 4 are at about 100% for everyone, so any slip there moves the next sprint. Sprint 5 has room: Jim and Jayasree each have about 1.3 pd free, "
        "which is where stretch work starts.", align="left", keep=True)

    d.h("9. Stretch and Later", 1)
    d.h("9.1 Stretch, in the order to pick them up", 2)
    st = [b for b in P.BACKLOG if b["tier"] == "S"]
    d.table(["Order", "ID", "Item", "Owner", "pd"], [[str(i + 1), b["id"], b["title"], NM(b["owner"]), f"{b['est']:g}"] for i, b in enumerate(st)], [0.6, 0.8, 5.4, 1.4, 0.8], size=9.5)
    d.h("9.2 Later, after Dec 25", 2)
    la = [b for b in P.BACKLOG if b["tier"] == "C"]
    d.table(["ID", "Module", "Item", "Owner", "pd"], [[b["id"], b["mod"], b["title"], NM(b["owner"]), f"{b['est']:g}"] for b in la], [0.8, 1.2, 4.8, 1.4, 0.8], size=9.5)

    d.h("10. Cut Line", 1)
    d.p("If the burn-up falls more than 2 pd behind the plan at the end of any sprint, drop these in order. Each cut keeps the product usable.", align="left", keep=True)
    d.table(["Order", "Cut", "What remains", "Saves"],
            [["1", "WH-60 notification core: keep the bell, drop grouping and preferences", "Plain in-app notices", "about 0.8 pd"],
             ["2", "WH-43 team calendar (keep the LWP export)", "Leave works; no calendar view", "about 0.8 pd"],
             ["3", "WH-33 inbox depth: drop bulk approve and filters", "Approve one by one with the timeline", "about 1.0 pd"],
             ["4", "WH-14 clients and work orders: keep client as text on the project", "As Zoho tags work today", "1.0 pd"],
             ["5", "WH-93 accessibility polish: keep the pass on the main screens only", "Core screens meet WCAG 2.2 AA", "about 0.8 pd"]],
            [0.6, 4.2, 2.8, 1.4], size=9.5)

    d.h("11. Risks", 1)
    d.figure(A("charts", "risk_map.png"), "Risk map: likelihood against impact.", 4.0)
    d.table(["ID", "Risk", "Likelihood", "Impact", "Mitigation", "Owner"],
            [[r[0], r[1], LVL[r[2]], LVL[r[3]], MITIGATION[r[0]], OWNER_R[r[0]]] for r in charts.RISKS], [0.4, 2.6, 0.8, 0.7, 3.6, 0.9], size=9)

    d.h("12. Ceremonies and Definition of Done", 1)
    d.table(["Ceremony", "When", "Length", "Purpose"],
            [["Daily stand-up", "Every working day, 10:00", "15 min", "What moved, what is blocked, what is next"],
             ["Sprint planning", "First day of each sprint", "45 min", "Confirm the sprint list against capacity"],
             ["Sprint review and demo", "Last day of each sprint (Dec 1 is the main one)", "45 min", "Show working software to stakeholders"],
             ["Retrospective", "Last day of each sprint", "30 min", "One thing to keep, one to change"]], [1.8, 3.1, 0.9, 3.2], size=9.5)
    d.bullets(["Reviewed by one other team member before merge.", "Business rules have unit tests; API tests run against real Postgres.",
               "Every change writes an audit event.", "Works for the roles it is meant for and is hidden from the others.",
               "No critical accessibility issue on the screen; demo-able in the shared environment."])

    d.h("13. Dependencies", 1)
    d.table(["Chain", "Why it matters"],
            [["WH-03 database schema, then WH-20 time API, then WH-30 approval engine, then WH-32 delegation", "The critical path for the Dec 1 demo and for approvals depth"],
             ["WH-04 sign-in, then every screen", "No one can test a screen without a signed-in user"],
             ["WH-05 app shell, then WH-21, WH-31, WH-40", "Jayasree's screens all sit on the shell and design system"],
             ["WH-40 leave types, then WH-41 apply, then WH-42 approve and fill timesheet", "Leave approval needs the approval engine (WH-30) and the time API (WH-20)"],
             ["WH-50 payslip upload, then WH-51 employee view", "Employees see nothing until HR publishes a batch"]], [5.0, 4.0], size=9.5)
    d.closing(14, "Jim, Janagan, Jayasree", "Initial draft of the WorkHub sprint plan.")
    return d


if __name__ == "__main__":
    pdf, n, missing = render.build(fn, OUT)
    print(pdf, n, "pages; headings without page:", missing)
    render.contact(pdf, os.path.join(H, "_ref", "sprint.png"), 0, 16, 4, 50)
