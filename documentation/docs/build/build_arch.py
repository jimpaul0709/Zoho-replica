"""WorkHub Architecture Document in the Ampera template (landscape, full-width diagrams)."""
import os
import render
from ampera_docx import AmperaDoc

H = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(H, "..", "assets", *p)
D = lambda n: A("diagrams", f"workhub-{n}.png")
OUT = os.path.join(H, "..", "WorkHub_Architecture_v0.1.docx")


def fn(pages):
    d = AmperaDoc("WorkHub Architecture\nDocument", "AMP_WH_ARC_001", "0.1", "12-Nov-2026", "WorkHub (working name)", landscape=True,
                  cover_lines=["WORKHUB ARCHITECTURE DOCUMENT"])
    d.toc()
    d.doc_info([("Prepared By", "Jim, Janagan, Jayasree"), ("Reviewed By", "To be assigned"), ("Status", "Draft for review"),
                ("Audience", "Engineers, reviewers, IT and security"),
                ("Related documents", "Design (AMP_WH_DSN_001), NFSD (AMP_WH_NFSD_001), FSD (AMP_WH_FSD_001)")])

    d.h("2. Goals and Constraints", 1)
    d.table(["Goal or constraint", "Consequence for the architecture"],
            [["Replace Zoho Projects, People and Payroll for Ampera by Dec 24 with three people", "One codebase per tier, one database, no extra infrastructure unless needed"],
             ["Web only, no mobile app, no activity monitoring", "No desktop agent; no native clients"],
             ["Sign-in: version 1 is email and password; version 2 is Microsoft Entra ID", "Version 1: users sign in with their work email and a password. Version 2: Entra ID sign-in, matched on work email"],
             ["Approved leave, holidays and timesheets must agree", "Leave module writes time entries in one transaction"],
             ["AI only suggests", "LLM is optional and never in the write path"],
             ["Hosting target not decided (Azure assumed)", "Containers and managed Postgres and storage; nothing cloud-specific in the code"]], [4.5, 4.5], size=10)

    d.h("3. System Context", 1)
    d.figure(D("context"), "WorkHub in its surroundings: people on the left, external services on the right.", 7.6)
    d.p("People reach WorkHub through the browser with an email and password sign-in (Microsoft sign-in comes in version 2). WorkHub calls out to Microsoft 365, GitHub or GitLab and an LLM service; Zoho is read once for import. "
        "Client users are an optional add-on with their own sign-in.", align="left")

    d.h("4. Containers", 1)
    d.figure(D("containers"), "Web app, API and worker share one database; files and external services sit behind them.", 7.8)
    d.table(["Container", "Technology", "Responsibility"],
            [["Web app", "React and TypeScript, built and run with Bun", "Screens only; types generated from the API schema"],
             ["API", "FastAPI, managed with uv", "Business rules, access control, audit, one module per area"],
             ["Worker", "Same Python code, second process", "Schedules, syncs, notifications, payslip batches; no web routes"],
             ["Postgres", "PostgreSQL", "All data, the job queue and the audit log"],
             ["File storage", "S3-compatible (Azure Blob or MinIO)", "Payslips and attachments, private, served by short-lived signed links"]], [1.5, 3.0, 4.5], size=10)

    d.h("5. Deployment", 1)
    d.figure(D("deployment"), "Target deployment: proxy and pods in an app zone, managed data in a private data zone.", 7.8)
    d.table(["Environment", "Purpose", "Notes"],
            [["Local", "Developer machines", "Docker Postgres, MinIO, hot reload"], ["Shared dev", "Demos and testing", "Seeded with realistic sample data"],
             ["Production", "Ampera staff", "API in 2 replicas, one worker, managed Postgres with backups; hosting target to be decided"]], [1.5, 2.5, 5.0], size=10)

    d.h("6. Runtime Views", 1)
    d.figure(D("seq-week"), "Submit and approve a week.", 6.0)
    d.figure(D("seq-leave"), "Leave approval fills the timesheet.", 6.0)
    d.h("6.1 Suggestions pipeline (later)", 2)
    d.figure(D("suggestions"), "Calendar and Git activity become suggestions the employee can accept.", 7.4)

    d.h("7. Data Architecture", 1)
    d.table(["Area", "Main tables", "Notes"],
            [["Organisation and work", "user, team, location, holiday, client, work_order, project, task, charge_code", "See the Design document for diagrams"],
             ["Time and approvals", "timesheet_week, time_entry, suggestion, approval, approval_step, delegation", "Time in integer minutes"],
             ["Leave and payslips", "leave_type, leave_balance, leave_request, comp_off_request, payslip_batch, payslip, document", "Files in object storage, rows hold keys"],
             ["Platform", "notification, notification_pref, audit_event, job, integration_account", "Audit is append-only"]], [2.0, 4.6, 2.4], size=10)

    d.h("8. Security Architecture", 1)
    d.figure(D("access"), "Every request: sign in, match an active user, load roles, check the record.", 4.6)
    d.table(["Control", "How"],
            [["Authentication", "Version 1: email and password (hashed, never stored in plain text). Version 2: Microsoft Entra ID (OIDC). Client users use a separate email link sign-in"], ["Authorisation", "Roles and reporting line in the API; menu hides, API enforces"],
             ["Data at rest", "Encrypted managed Postgres and storage; integration tokens encrypted"], ["Data in transit", "TLS everywhere, including to Postgres"],
             ["Files", "Private bucket, signed links that expire, content-type checks on upload"], ["Audit", "Every change and every payslip view or download"]], [2.0, 7.0], size=10)

    d.h("9. Integrations", 1)
    d.table(["Service", "Purpose", "Access", "If it fails"],
            [["Microsoft Entra ID (version 2)", "Sign-in", "OIDC, tenant app registration", "No Entra sign-in; password sign-in still works; status banner"],
             ["Outlook calendar (later)", "Suggestions", "Read-only, per-user consent", "No suggestions; logging time still works"],
             ["Teams (stretch)", "Notices", "Incoming webhook or bot", "In-app notice remains"],
             ["GitHub and GitLab (later)", "Suggestions", "OAuth per user", "No suggestions"],
             ["LLM service (later)", "Tidy notes, weekly status", "API key held as a secret", "Rules still decide; text stays as typed"],
             ["Zoho (one-off)", "Import", "API or CSV, dry run first", "Re-run is safe (keyed on Zoho IDs)"]], [2.0, 1.6, 2.7, 2.7], size=10)

    d.h("10. Technology Stack", 1)
    d.table(["Layer", "Choice", "Why"],
            [["Web", "React, TypeScript, Vite, Bun", "Fast builds; team familiarity"], ["API and worker", "Python, FastAPI, uv", "Rules and AI in one language; typed schema"],
             ["Database", "PostgreSQL", "Relational model, transactions, job queue table"], ["Files", "S3-compatible storage", "Signed links, portable"],
             ["Tests", "pytest, Playwright", "Rules in unit tests; four end-to-end journeys"], ["CI", "Lint, tests, build on every push", "Catch breakage before review"]], [1.6, 3.0, 4.4], size=10)

    d.h("11. Quality Scenarios", 1)
    d.table(["Quality", "Scenario", "Target (proposed)"],
            [["Performance", "Open the current week with 30 entries", "95th percentile under 1.5 s"], ["Availability", "API replica fails during working hours", "Other replica serves; no user action"],
             ["Security", "Employee requests another person's payslip by id", "Not found, and the attempt is logged"], ["Recoverability", "Database corruption", "Restore from backup; loss of at most 24 h"],
             ["Modifiability", "Add a new approvable item", "One new subject type in the approval engine; no inbox change"]], [1.6, 4.2, 3.2], size=10)

    d.h("12. Failure Modes", 1)
    d.table(["Failure", "Effect", "Handling"],
            [["Worker is down", "No reminders or notices", "Jobs queue in Postgres and run on restart; failed-jobs list for admins"],
             ["Postgres is down", "Application unavailable", "Managed service with backups; status page"],
             ["Entra ID unavailable (version 2)", "No new Entra sign-ins; password sign-in still works", "Existing sessions continue until expiry"],
             ["Integration token expired", "Suggestions stop for that user", "Reconnect banner; time logging unaffected"]], [2.2, 2.6, 4.2], size=10)

    d.h("13. Decision Summary", 1)
    d.table(["Decision", "Choice", "Alternative not taken"],
            [["Stack", "React on Bun, FastAPI on uv, Postgres", "One Next.js app"], ["Queue", "Postgres table", "Redis"],
             ["Files", "Private object storage with signed links", "Files in the database"], ["Client access", "Separate identity and sign-in", "Client role in the main user table"]], [2.0, 3.5, 3.5], size=10)
    d.closing(14, "Jim, Janagan, Jayasree", "Initial draft of the WorkHub architecture document.")
    return d


if __name__ == "__main__":
    pdf, n, missing = render.build(fn, OUT)
    print(pdf, n, "pages; headings without page:", missing)
    render.contact(pdf, os.path.join(H, "_ref", "arch.png"), 0, 18, 6, 40)
