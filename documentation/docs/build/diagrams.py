"""WorkHub diagrams, redrawn in the Ampera skin from the Mermaid sources in assets/diagrams/workhub-diagrams.md."""
import os
import sys
from dd import D, KINDS, esc, ink, SOFT, MUTED, INK, ACCENT, PAPER, MONO

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "diagrams"))


# ---------------------------------------------------------------- helpers
def entity(d, id, x, y, w, name, fields, focal=False):
    h = 28 + 14 * len(fields) + 10
    d.N[id] = (x, y, w, h)
    fill, stroke, _ = KINDS["focal" if focal else "backend"]
    tcol = ACCENT if focal else SOFT
    s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PAPER}"/>',
         f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1"/>',
         f'<line x1="{x}" y1="{y + 28}" x2="{x + w}" y2="{y + 28}" stroke="{stroke}" stroke-opacity="0.4" stroke-width="0.8"/>',
         f'<rect x="{x + 8}" y="{y + 8}" width="41" height="12" rx="2" fill="transparent" stroke="{tcol}" stroke-opacity="0.55" stroke-width="0.8"/>',
         f'<text x="{x + 28.5}" y="{y + 17}" fill="{tcol}" font-size="7" font-family="{MONO}" text-anchor="middle" letter-spacing="0.08em">ENTITY</text>',
         f'<text x="{x + 58}" y="{y + 19}" fill="{INK}" font-size="12" font-weight="700" font-family="Calibri, Arial, sans-serif">{esc(name)}</text>']
    for i, f in enumerate(fields):
        s.append(f'<text x="{x + 10}" y="{y + 28 + 14 * i + 14}" fill="{MUTED}" font-size="9" font-family="{MONO}">{esc(f)}</text>')
    d.nodes.append("".join(s))
    return h


def rel(d, pts, label, ca, cb, side="right"):
    d.edge(pts, label=label, seg=0 if len(pts) == 2 else (1 if len(pts) == 4 and side == "left" else 0), side="above" if pts[0][1] == pts[1][1] else side, marker=None)
    for (p, q, c) in ((pts[0], pts[1], ca), (pts[-1], pts[-2], cb)):
        dx, dy = q[0] - p[0], q[1] - p[1]
        if abs(dx) >= abs(dy):
            x, y, anc = p[0] + (14 if dx > 0 else -14), p[1] - 6, "middle"
        else:
            x, y, anc = p[0] + 8, p[1] + (14 if dy > 0 else -8), "start"
        d.over.append(f'<text x="{x}" y="{y}" fill="{INK}" font-size="9" font-weight="700" font-family="{MONO}" text-anchor="{anc}">{esc(c)}</text>')


def er_legend(d):
    d.over.append(f'<text x="40" y="{d.H - 32}" fill="{MUTED}" font-size="9" font-family="{MONO}"># primary key   → foreign key   1 one   N many   0..1 optional one</text>')
    d.over.append(f'<line x1="40" y1="{d.H - 48}" x2="{d.W - 40}" y2="{d.H - 48}" stroke="{ink(.10)}" stroke-width="0.8"/>')


def seq(slug, title, desc, actors, msgs, bars, H, W=880):
    d = D(slug, title, desc, W, H, "Sequence")
    xs = [100 + i * ((W - 80 - 120) / (len(actors) - 1)) for i in range(len(actors))]
    for (name, kind), x in zip(actors, xs):
        d.node(name, int(x - 60), 32, 120, 48, name, kind=kind)
        d.zones.append(f'<line x1="{x:g}" y1="80" x2="{x:g}" y2="{H - 60}" stroke="{ink(.20)}" stroke-width="1" stroke-dasharray="3,3"/>')
    for (i, y0, y1) in bars:
        d.zones.append(f'<rect x="{xs[i] - 4:g}" y="{y0}" width="8" height="{y1 - y0}" fill="{ink(.06)}" stroke="{MUTED}" stroke-width="0.8"/>')
    for k, (a, b, label, kind) in enumerate(msgs):
        y = 120 + 40 * k
        if kind == "self":
            x = xs[a] + 4
            d.edge([(x, y), (x + 32, y), (x + 32, y + 20), (x, y + 20)], at=(x + 32 + 8 + (len(label) * 5.2 + 12) / 2, y + 10), label=label)
            continue
        sgn = 1 if xs[b] > xs[a] else -1
        pts = [(xs[a] + 4 * sgn, y), (xs[b] - 4 * sgn, y)]
        style = dict(call=dict(), ret=dict(dashed=True), asyn=dict(dashed=True, marker="open"), head=dict(kind="accent"))[kind]
        d.edge(pts, label=label, **style)
    d.legend([("arrow", "default", "Call"), ("arrow", "default-d", "Return"), ("arrow", "accent", "Headline result")])
    return d


# ---------------------------------------------------------------- 01 context
def context():
    d = D("workhub-context", "WorkHub system context",
          "WorkHub sits between Ampera's staff and the Microsoft 365, Git, LLM and Zoho services it connects to.", 880, 560, "Architecture")
    d.node("staff", 40, 96, 180, 56, "Employees and managers", ["web app, SSO"], "input")
    d.node("ops", 40, 244, 180, 56, "HR, Finance and Admin", ["web app, SSO"], "input")
    d.node("cli", 40, 408, 180, 56, "Client users", ["optional add-on"], "optional")
    d.node("wh", 400, 216, 160, 112, "WorkHub", ["web app, API, worker"], "focal", tag="SYSTEM")
    d.node("m365", 680, 100, 160, 56, "Microsoft 365", ["Entra ID, Outlook, Teams"], "external")
    d.node("git", 680, 204, 160, 56, "GitHub and GitLab", ["commits and PRs"], "external")
    d.node("llm", 680, 308, 160, 56, "LLM service", ["draft text only"], "external")
    d.node("zoho", 680, 412, 160, 56, "Zoho", ["one-off import"], "optional")
    d.edge([(220, 124), (316, 124), (316, 240), (400, 240)], "LOG · APPROVE", 0, kind="accent")
    d.edge([(220, 272), (400, 272)], "MANAGE+UPLOAD")
    d.edge([(220, 436), (300, 436), (300, 304), (400, 304)], "REPORTS", 0, dashed=True)
    d.edge([(560, 240), (584, 240), (584, 128), (680, 128)], "SSO · CALENDAR", 2, kind="link")
    d.edge([(680, 232), (612, 232), (612, 264), (560, 264)], "COMMITS", 0, kind="link")
    d.edge([(560, 288), (612, 288), (612, 336), (680, 336)], "DRAFTS", 2, kind="link")
    d.edge([(680, 440), (584, 440), (584, 312), (560, 312)], "ONE-OFF IMPORT", 0, dashed=True)
    d.legend([("box", "focal", "WorkHub"), ("box", "input", "People"), ("box", "external", "External service"),
              ("box", "optional", "Optional / one-off"), ("arrow", "link", "Integration")])
    return d


# ---------------------------------------------------------------- 02 containers
def containers():
    d = D("workhub-containers", "WorkHub containers",
          "The web app calls one API; a worker shares the same code and database; files, Microsoft 365, Git and the LLM are reached from the API or worker.", 880, 620, "Architecture")
    d.zone(336, 48, 208, 392, "WorkHub code")
    d.node("web", 40, 80, 104, 64, "Web app", ["React, Bun"], "input")
    d.node("api", 360, 80, 160, 64, "API", ["FastAPI, uv"], "focal", tag="API")
    d.node("wrk", 360, 360, 160, 64, "Worker", ["same code, 2nd process"], "backend", tag="WORKER")
    d.node("files", 120, 216, 144, 64, "File storage", ["payslips, attachments"], "store")
    d.node("pg", 616, 216, 144, 64, "Postgres", ["data, jobs, audit"], "store")
    d.node("m365", 704, 80, 136, 64, "Microsoft 365", ["Entra, Outlook, Teams"], "external")
    d.node("git", 300, 484, 160, 56, "GitHub, GitLab", ["commits and PRs"], "external")
    d.node("llm", 500, 484, 160, 56, "LLM service", ["draft text only"], "external")
    d.edge([(144, 112), (360, 112)], "HTTPS JSON", 0, kind="link")
    d.edge([(360, 132), (192, 132), (192, 216)], "SIGNED URLS", 0, side="below")
    d.edge([(520, 100), (704, 100)], "OIDC SIGN-IN", 0, kind="link")
    d.edge([(520, 124), (672, 124), (672, 216)], "SQL", 1, side="right")
    d.edge([(360, 392), (192, 392), (192, 280)], "BATCHES", 0, side="below")
    d.edge([(520, 368), (688, 368), (688, 280)], "JOBS", 0)
    d.edge([(520, 396), (776, 396), (776, 144)], "CALENDAR,TEAMS", 0, side="below", kind="link")
    d.edge([(400, 424), (400, 484)], "COMMITS", 0, side="right", kind="link")
    d.edge([(480, 424), (480, 452), (580, 452), (580, 484)], "DRAFTS", 1, kind="link")
    d.legend([("box", "focal", "Request path"), ("box", "store", "Store"), ("box", "external", "External service"), ("arrow", "link", "Integration")])
    return d


# ---------------------------------------------------------------- 03 deployment
def deployment():
    d = D("workhub-deployment", "WorkHub deployment (target)",
          "Browser traffic enters through a proxy to the API; the API and worker use Postgres and object storage in a private data zone; the worker reaches Microsoft 365, GitHub and the LLM over HTTPS.", 880, 520, "Deployment")
    d.zone(24, 48, 136, 290, "Internet")
    d.zone(208, 48, 352, 290, "App zone")
    d.zone(640, 48, 216, 290, "Data zone")
    d.node("br", 40, 120, 104, 64, "Browser", ["employee device"], "input")
    d.node("px", 224, 112, 112, 104, "Edge proxy", None, "backend", tag="MANAGED", chip=("web build", "v0.1.0"))
    d.node("api", 400, 112, 144, 104, "API", None, "backend", tag="POD", badge="x2", chip=("workhub-api", "v0.1.0"))
    d.node("wk", 400, 232, 144, 88, "Worker", None, "backend", tag="POD", chip=("workhub-worker", "v0.1.0"))
    d.node("pg", 656, 112, 184, 104, "Postgres", ["primary + backups"], "focal", tag="MANAGED", chip=("postgres", "16"))
    d.node("bl", 656, 232, 184, 88, "Object storage", ["private, signed URLs"], "store", tag="MANAGED")
    d.node("ext", 400, 384, 144, 56, "Microsoft 365, Git, LLM", ["egress only"], "external")
    d.edge([(144, 152), (224, 152)], "HTTPS:443", 0, kind="link")
    d.edge([(336, 152), (400, 152)], "HTTP:8000", 0)
    d.edge([(544, 152), (656, 152)], "TLS:5432", 0, kind="link")
    d.edge([(544, 264), (608, 264), (608, 176), (656, 176)], "TLS:5432", 0, side="below", kind="link")
    d.edge([(544, 300), (656, 300)], "HTTPS:443", 0, side="below", kind="link")
    d.edge([(472, 320), (472, 384)], "HTTPS:443", 0, side="right", kind="link")
    d.legend([("box", "focal", "Single point of failure"), ("box", "backend", "Service"), ("box", "store", "Store"), ("arrow", "link", "Crosses a zone")])
    return d


# ---------------------------------------------------------------- 04-06 ER
def er_org():
    d = D("workhub-er-org", "Data model: organisation and work",
          "Clients fund projects through work orders; people belong to locations and teams and are members of projects; teams may use charge codes.", 880, 600, "ER / data model")
    entity(d, "client", 40, 48, 176, "CLIENT", ["# id", "name"])
    entity(d, "wo", 40, 200, 176, "WORK_ORDER", ["# id", "code (SOW)", "→ client_id", "start, end dates"])
    entity(d, "proj", 40, 384, 176, "PROJECT", ["# id", "key (ATPL-106)", "name", "→ work_order_id", "→ manager_id", "visibility"])
    entity(d, "loc", 352, 200, 176, "LOCATION", ["# id", "name", "country"])
    entity(d, "user", 352, 384, 176, "USER", ["# id", "employee_code", "email", "→ location_id", "→ manager_id", "active"], focal=True)
    entity(d, "cc", 664, 200, 176, "CHARGE_CODE", ["# id", "code", "name"])
    entity(d, "team", 664, 384, 176, "TEAM", ["# id", "name"])
    rel(d, [(128, 114), (128, 200)], "HAS", "1", "N")
    rel(d, [(128, 294), (128, 384)], "FUNDS", "1", "N")
    rel(d, [(216, 444), (352, 444)], "MEMBERS", "N", "N")
    rel(d, [(440, 280), (440, 384)], "WORKS AT", "1", "N")
    rel(d, [(528, 444), (664, 444)], "MEMBER OF", "N", "N")
    rel(d, [(752, 384), (752, 280)], "MAY USE", "N", "N")
    er_legend(d)
    return d


def er_time():
    d = D("workhub-er-time", "Data model: time and approvals",
          "A user owns weekly timesheets of time entries; submitting a week creates an approval with a step log; suggestions become entries when accepted; approvers can delegate.", 880, 600, "ER / data model")
    entity(d, "deleg", 352, 48, 176, "DELEGATION", ["# id", "from_user → to_user", "start, end dates"])
    entity(d, "step", 664, 48, 176, "APPROVAL_STEP", ["# id", "→ approval_id", "actor, action", "reason", "at"])
    entity(d, "user", 40, 200, 176, "USER", ["# id", "name", "→ manager_id"])
    entity(d, "week", 352, 200, 176, "TIMESHEET_WEEK", ["# id", "→ user_id", "week_start", "status", "locked_at"], focal=True)
    entity(d, "appr", 664, 200, 176, "APPROVAL", ["# id", "subject (week, leave)", "→ requester_id", "→ approver_id", "status", "due_at"])
    entity(d, "sug", 40, 384, 176, "SUGGESTION", ["# id", "→ user_id", "date, minutes", "source", "evidence", "status"])
    entity(d, "te", 352, 384, 176, "TIME_ENTRY", ["# id", "→ week_id", "date", "minutes", "billable", "source", "→ task / charge code"])
    entity(d, "task", 664, 384, 176, "TASK", ["# id", "key (AS1-T4)", "→ project_id", "status"])
    rel(d, [(216, 240), (352, 240)], "OWNS", "1", "N")
    rel(d, [(440, 308), (440, 384)], "HAS", "1", "N")
    rel(d, [(528, 450), (664, 450)], "LOGS ON", "N", "1")
    rel(d, [(216, 450), (352, 450)], "BECOMES", "0..1", "1")
    rel(d, [(528, 240), (664, 240)], "NEEDS", "1", "N")
    rel(d, [(752, 200), (752, 156)], "LOGS", "1", "N")
    rel(d, [(352, 88), (128, 88), (128, 200)], "HANDS OVER", "N", "1")
    er_legend(d)
    return d


def er_leave():
    d = D("workhub-er-leave", "Data model: leave and payslips",
          "Users hold leave balances per type, apply for leave and comp-off, receive payslips from uploaded batches, and own documents.", 880, 600, "ER / data model")
    entity(d, "lt", 40, 48, 176, "LEAVE_TYPE", ["# id", "name", "paid", "accrual rule", "carry-forward cap"])
    entity(d, "doc", 352, 48, 176, "DOCUMENT", ["# id", "→ user_id", "type (Form 16)", "year", "file_key"])
    entity(d, "batch", 664, 48, 176, "PAYSLIP_BATCH", ["# id", "month", "→ uploaded_by", "status", "match report"])
    entity(d, "lb", 40, 200, 176, "LEAVE_BALANCE", ["# id", "→ user_id", "→ leave_type_id", "leave year", "opening, accrued", "used, adjusted"])
    entity(d, "user", 352, 200, 176, "USER", ["# id", "employee_code", "email"], focal=True)
    entity(d, "slip", 664, 200, 176, "PAYSLIP", ["# id", "→ batch_id", "→ user_id", "file_key"])
    entity(d, "lr", 352, 384, 176, "LEAVE_REQUEST", ["# id", "→ user_id", "→ leave_type_id", "from, to dates", "day portions", "status"])
    entity(d, "co", 664, 384, 176, "COMP_OFF_REQUEST", ["# id", "→ user_id", "worked date", "minutes", "status"])
    rel(d, [(440, 156), (440, 200)], "FOR", "N", "1")
    rel(d, [(352, 240), (216, 240)], "HAS", "1", "N")
    rel(d, [(128, 156), (128, 200)], "OF TYPE", "1", "N")
    rel(d, [(440, 280), (440, 384)], "APPLIES", "1", "N")
    rel(d, [(528, 240), (664, 240)], "RECEIVES", "1", "N")
    rel(d, [(528, 262), (600, 262), (600, 444), (664, 444)], "EARNS", "1", "N", side="left")
    rel(d, [(752, 156), (752, 200)], "CONTAINS", "1", "N")
    er_legend(d)
    return d


# ---------------------------------------------------------------- 07 state
def state():
    d = D("workhub-week-lifecycle", "Timesheet week lifecycle",
          "A week moves from draft to submitted, then is approved and locked or sent back; a locked week reopens only through an approved edit request.", 880, 520, "State machine")
    d.node("draft", 96, 128, 120, 56, "Draft", ["employee edits"], rx=8)
    d.node("sub", 336, 128, 128, 56, "Submitted", ["waiting for manager"], rx=8)
    d.node("app", 584, 128, 144, 56, "Approved", ["week is locked"], "focal", rx=8)
    d.node("back", 336, 312, 128, 56, "Sent back", ["reason shown"], rx=8)
    d.node("edit", 584, 312, 144, 56, "Edit requested", ["stretch: WH-22"], "optional", rx=8)
    d.dot(56, 156)
    d.edge([(62, 156), (96, 156)])
    d.edge([(216, 156), (336, 156)], "SUBMIT", 0)
    d.edge([(464, 156), (584, 156)], "APPROVE", 0, kind="accent")
    d.edge([(384, 128), (384, 100), (416, 100), (416, 128)], "ESCALATE", at=(400, 84))
    d.edge([(400, 184), (400, 312)], "SEND BACK", 0, side="right")
    d.edge([(336, 340), (156, 340), (156, 184)], "EMPLOYEE EDITS", 0)
    d.edge([(624, 184), (624, 312)], None)
    d.edges.append(d.label_mask(579, 232, "REQUEST EDIT"))
    d.edge([(688, 312), (688, 184)], None, dashed=True)
    d.edges.append(d.label_mask(718, 250, "REJECT"))
    d.edge([(656, 368), (656, 420), (116, 420), (116, 184)], "ALLOW EDIT", 1, dashed=True)
    d.legend([("box", "focal", "Locked outcome"), ("box", "optional", "Stretch feature"), ("arrow", "accent", "Happy path"), ("arrow", "default-d", "Exception path")])
    return d


# ---------------------------------------------------------------- 08-09 sequences
def seq_week():
    return seq("workhub-seq-week", "Submit and approve a week",
               "An employee submits a week, the API checks the rules and notifies the manager, who approves it; the API locks the week and notifies the employee.",
               [("Employee", "input"), ("Web app", "backend"), ("API", "focal"), ("Worker", "backend"), ("Manager", "input")],
               [(0, 1, "1 SUBMIT WEEK", "call"), (1, 2, "2 POST SUBMIT", "call"), (2, 2, "3 CHECK RULES", "self"),
                (2, 1, "4 SUBMITTED", "ret"), (2, 3, "5 QUEUE NOTICE", "asyn"), (3, 4, "6 NOTIFY", "asyn"),
                (4, 1, "7 APPROVE", "call"), (1, 2, "8 POST APPROVE", "call"), (2, 2, "9 LOCK + AUDIT", "self"),
                (2, 1, "10 APPROVED", "head"), (2, 3, "11 NOTIFY", "asyn"), (3, 0, "12 APPROVED", "asyn")],
               [(1, 120, 240), (2, 160, 280), (3, 280, 320), (1, 360, 480), (2, 400, 520), (3, 520, 560)], 660)


def seq_leave():
    return seq("workhub-seq-leave", "Leave approval fills the timesheet",
               "Applying for leave creates an approval; when the manager approves it, the leave module deducts the balance and the time module fills the week.",
               [("Employee", "input"), ("Leave module", "backend"), ("Approval engine", "focal"), ("Time module", "backend"), ("Manager", "input")],
               [(0, 1, "1 APPLY LEAVE", "call"), (1, 1, "2 CHECK RULES", "self"), (1, 2, "3 CREATE", "call"),
                (2, 4, "4 NOTIFY", "asyn"), (4, 2, "5 APPROVE", "call"), (2, 1, "6 APPROVED", "call"),
                (1, 1, "7 DEDUCT DAYS", "self"), (1, 3, "8 FILL WEEK", "call"), (3, 1, "9 DONE", "ret"),
                (1, 0, "10 APPROVED", "head")],
               [(1, 120, 200), (2, 160, 220), (2, 280, 320), (1, 320, 440), (3, 360, 400)], 600)


# ---------------------------------------------------------------- 10 AI pipeline
def pipeline():
    d = D("workhub-suggestions", "How suggested time entries are made",
          "Calendar and Git activity are synced, matched to projects by rules, optionally tidied by an LLM, stored as suggestions and shown in the week view for the employee to accept.",
          880, 440, "Architecture")
    d.node("cal", 40, 72, 128, 56, "Outlook calendar", ["meetings"], "external")
    d.node("git", 40, 192, 128, 56, "GitHub, GitLab", ["commits and PRs"], "external")
    d.node("sync", 264, 128, 128, 64, "Sync job", ["nightly + on demand"], "backend", tag="WORKER")
    d.node("match", 472, 128, 128, 64, "Matching rules", ["project key, client"], "focal", tag="RULES")
    d.node("store", 680, 128, 128, 64, "Suggestions", ["pending, owner only"], "store")
    d.node("ui", 680, 296, 128, 64, "Week view", ["side panel"], "backend")
    d.node("entry", 472, 296, 128, 64, "Time entries", ["after accept"], "store")
    d.node("llm", 264, 296, 128, 64, "LLM service", ["tidy notes"], "optional")
    d.edge([(168, 100), (232, 100), (232, 148), (264, 148)], "EVENTS", 0, kind="link")
    d.edge([(168, 220), (232, 220), (232, 172), (264, 172)], "COMMITS", 0, kind="link")
    d.edge([(392, 160), (472, 160)], "CANDIDATES", 0)
    d.edge([(600, 160), (680, 160)], "PROPOSALS", 0)
    d.edge([(744, 192), (744, 296)], "SIDE PANEL", 0, side="right")
    d.edge([(680, 328), (600, 328)], "ACCEPT", 0, kind="accent")
    d.edge([(536, 192), (536, 240), (328, 240), (328, 296)], "TIDY NOTES", 1, dashed=True)
    d.legend([("box", "focal", "Rules decide first"), ("box", "optional", "Optional"), ("arrow", "accent", "Employee action")])
    return d


# ---------------------------------------------------------------- 11 sitemap
def sitemap():
    d = D("workhub-sitemap", "WorkHub sitemap",
          "Five areas under WorkHub: My space, Manage, Work, Admin and Insights, each listing its pages.", 880, 380, "Tree")
    d.node("root", 360, 48, 160, 56, "WorkHub", ["web app"], "focal")
    cols = [("My space", ["Week timesheet", "Leave", "Payslips", "Notifications"]),
            ("Manage", ["Approvals inbox", "Team calendar", "Team dashboard *"]),
            ("Work", ["Clients", "Projects", "Tasks"]),
            ("Admin", ["Users and roles", "Holidays, org", "Leave types", "Payslip batches", "Audit log"]),
            ("Insights", ["Reports *", "Status reports *"])]
    d.edge([(440, 104), (440, 144)], marker=None)
    d.edge([(112, 144), (768, 144)], marker=None)
    for i, (name, subs) in enumerate(cols):
        x = 40 + i * 164
        cx = x + 72
        d.edge([(cx, 144), (cx, 184)], marker=None)
        d.node(name, x, 184, 144, 112, name, subs, "backend")
    d.legend([("box", "focal", "Root"), ("box", "backend", "Area"), ])
    d.over.append(f'<text x="360" y="{d.H - 32}" fill="{MUTED}" font-size="9" font-family="{MONO}">* stretch or later</text>')
    return d


# ---------------------------------------------------------------- 12 access flow
def access():
    d = D("workhub-access", "Sign-in and record access",
          "Every request starts with a Microsoft sign-in, matches an active user, loads roles and reporting line, and checks whether the person may see the record.", 720, 700, "Flowchart")
    d.node("start", 180, 40, 160, 40, "Open WorkHub", None, "input", shape="pill")
    d.node("sso", 180, 112, 160, 56, "Sign in with Microsoft", ["Entra ID"], "backend")
    d.node("d1", 160, 208, 200, 88, "Email matches\nan active user?", None, "backend", shape="diamond")
    d.node("deny", 460, 224, 160, 56, "Access denied", ["no data shown"], "security")
    d.node("roles", 180, 332, 160, 56, "Load roles", ["and reporting line"], "backend")
    d.node("d2", 160, 428, 200, 88, "Allowed to see\nthis record?", None, "backend", shape="diamond")
    d.node("hide", 460, 444, 160, 56, "Return not found", ["attempt is logged"], "security")
    d.node("show", 180, 552, 160, 56, "Show the record", ["audit on change"], "focal")
    d.edge([(260, 80), (260, 112)])
    d.edge([(260, 168), (260, 208)])
    d.edge([(260, 296), (260, 332)], "YES", 0, side="right")
    d.edge([(360, 252), (460, 252)], "NO", 0, kind="accent", dashed=True)
    d.edge([(260, 388), (260, 428)])
    d.edge([(360, 472), (460, 472)], "NO", 0, kind="accent", dashed=True)
    d.edge([(260, 516), (260, 552)], "YES", 0, side="right")
    d.legend([("box", "focal", "Allowed"), ("box", "security", "Blocked"), ("arrow", "accent-d", "Denied path")])
    return d


ALL = [context, containers, deployment, er_org, er_time, er_leave, state, seq_week, seq_leave, pipeline, sitemap, access]

if __name__ == "__main__":
    from PIL import Image
    only = sys.argv[1:]
    pngs = []
    for fn in ALL:
        if only and fn.__name__ not in only:
            continue
        d = fn()
        warns = d.check()
        pngs.append(d.save(OUT))
        print(d.slug, "OK" if not warns else warns)
    ims = [Image.open(p) for p in pngs]
    tw = 520
    th = [int(im.height * tw / im.width) for im in ims]
    cols = 3
    rows = (len(ims) + cols - 1) // cols
    rh = [max(th[r * cols:(r + 1) * cols]) for r in range(rows)]
    sheet = Image.new("RGB", (cols * tw + 6 * (cols + 1), sum(rh) + 6 * (rows + 1)), (120, 120, 120))
    y = 6
    for r in range(rows):
        for c in range(cols):
            k = r * cols + c
            if k < len(ims):
                sheet.paste(ims[k].resize((tw, th[k])), (6 + c * (tw + 6), y))
        y += rh[r] + 6
    sheet.save(os.path.join(OUT, "_contact.png"))
