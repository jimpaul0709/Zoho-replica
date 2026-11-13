"""WorkHub Non-Functional Specification Document in the Ampera template."""
import os
import render
import charts
from ampera_docx import AmperaDoc

H = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(H, "..", "assets", *p)
D = lambda n: A("diagrams", f"workhub-{n}.png")
OUT = os.path.join(H, "..", "WorkHub_NFSD_v0.1.docx")
M, S_ = "Must", "Should"

# category: (heading, intro, [(id, requirement, target, verification, priority)])
NFR = [
    ("PERF", "Performance", "Targets are proposed and apply to a typical office connection.", [
        ("PERF-01", "Open the current week with 30 entries", "95th percentile under 1.5 s", "Browser timing test", M),
        ("PERF-02", "API reads and writes", "Reads under 300 ms, writes under 500 ms at the 95th percentile", "API load test", M),
        ("PERF-03", "Approvals inbox with 100 items", "Under 1.5 s", "Browser timing test", M),
        ("PERF-04", "Match a payslip batch of 300 PDFs", "Preview ready in 2 minutes or less", "Batch test", S_),
        ("PERF-05", "Nightly jobs (accrual, syncs)", "Finish within 30 minutes", "Job log review", S_),
        ("PERF-06", "First load on a 10 Mbps link", "Under 3 s", "Lighthouse run", S_)]),
    ("CAP", "Capacity and Scalability", "Ampera headcount is not confirmed; sizing assumes up to 500 users.", [
        ("CAP-01", "Active users", "Design for 500; test at 200", "Load test", M),
        ("CAP-02", "Peak concurrency (Friday afternoon)", "100 users", "Load test", M),
        ("CAP-03", "Data volume", "Five years of time entries (about 3 million rows) without slower queries", "Query plan review", S_),
        ("CAP-04", "Scale-out", "API runs as two or more replicas; the worker as one", "Deployment check", M)]),
    ("AVL", "Availability, Backup and Recovery", "Working hours are Monday to Friday, 08:00 to 20:00 IST.", [
        ("AVL-01", "Availability in working hours", "99.5% per month", "Uptime monitor", M),
        ("AVL-02", "Backups", "Daily, kept 30 days", "Backup report", M),
        ("AVL-03", "Recovery", "Loss of at most 24 hours; restored within 4 hours", "Restore test before release", M),
        ("AVL-04", "Replica failure", "The other replica serves with no user action", "Failover test", M)]),
    ("SEC", "Security", "Controls follow the access flow in the Architecture document.", [
        ("SEC-01", "Staff sign in with Microsoft Entra ID only", "No local passwords", "Configuration review", M),
        ("SEC-02", "Session lifetime", "60 minutes idle, 12 hours absolute", "Session test", M),
        ("SEC-03", "Access control", "Enforced in the API; deny by default; menus only hide", "Permission test sweep (WH-91)", M),
        ("SEC-04", "Payslip files", "Private storage; signed links that expire in 5 minutes", "Security review", M),
        ("SEC-05", "Audit", "Every change, and every payslip view or download; kept 2 years", "Audit coverage check", M),
        ("SEC-06", "Secrets", "Held in environment or secret store, never in code", "CI secret scan", M),
        ("SEC-07", "Integration tokens", "Encrypted at rest", "Code review", M),
        ("SEC-08", "Uploads", "Type checked by content; 10 MB per file, 200 MB per ZIP", "Upload tests", M),
        ("SEC-09", "Rate limits", "Sign-in and API limited per user and address", "Load test", S_),
        ("SEC-10", "Dependencies", "Scanned for known vulnerabilities in CI", "CI report", S_),
        ("SEC-11", "Client users (add-on)", "Cannot reach any staff API", "Negative tests", M)]),
    ("PRV", "Privacy and Compliance", "Needs review by Compliance. India's DPDP Rules apply in stages, with most obligations from about 2027.", [
        ("PRV-01", "Data collected", "Only what the features need; no monitoring, screenshots or keystrokes", "Design review", M),
        ("PRV-02", "Suggestions and their evidence", "Visible only to their owner", "Permission tests", M),
        ("PRV-03", "Notice to staff", "States what data is held, why and for how long", "Compliance sign-off", M),
        ("PRV-04", "Retention", "Periods for time, leave and payslips: TBD with HR and Compliance", "Policy document", M),
        ("PRV-05", "Access and erasure requests", "A documented process", "Process review", S_),
        ("PRV-06", "Payslip contents", "Hidden from Admin unless the person also holds HR", "Permission tests", M)]),
    ("UX", "Usability and Accessibility", "Desktop first; there is no mobile app.", [
        ("UX-01", "Accessibility", "WCAG 2.2 AA on the core screens", "Accessibility pass (WH-93)", M),
        ("UX-02", "Keyboard", "Week grid and inbox usable without a mouse", "Manual test", M),
        ("UX-03", "Browsers", "Current and previous two versions of Chrome, Edge, Firefox and Safari", "Browser test", M),
        ("UX-04", "Errors", "Plain sentences that say how to fix the problem", "Review", M),
        ("UX-05", "Screen width", "Works from 1024 px wide", "Browser test", S_)]),
    ("MNT", "Maintainability and Testability", "Keeps a three-person team able to change the system safely.", [
        ("MNT-01", "Unit tests", "Every business rule; at least 80% coverage in rule modules", "Coverage report", M),
        ("MNT-02", "API tests", "Run against real Postgres", "CI", M),
        ("MNT-03", "End-to-end tests", "Four journeys: week, approval, leave, payslip (client portal journey is added with the add-on, later)", "Playwright run", M),
        ("MNT-04", "Quality gate", "Lint, types and tests must pass before merge", "CI", M),
        ("MNT-05", "Migrations", "Versioned and repeatable", "Migration test", M),
        ("MNT-06", "Documents", "README and runbook current at release", "Review", S_)]),
    ("OBS", "Observability and Operations", "", [
        ("OBS-01", "Logs", "Structured, with a request id", "Log review", M), ("OBS-02", "Alerts", "Errors and failed jobs reach the team channel", "Alert test", S_),
        ("OBS-03", "Failed jobs", "Listed for admins with a retry button", "Manual test", M), ("OBS-04", "Health", "Health endpoints for API and worker", "Monitor", M)]),
    ("LOC", "Compatibility and Localisation", "", [
        ("LOC-01", "Time zone", "Shown in IST; stored in UTC", "Test", M), ("LOC-02", "Date format", "dd-Mmm-YYYY in documents and reports", "Review", M),
        ("LOC-03", "Leave year", "April to March, configurable", "Test", M), ("LOC-04", "Work week and holidays", "Configurable per location", "Test", M)]),
    ("INT", "Integration Reliability", "", [
        ("INT-01", "Failure isolation", "An integration failure never blocks logging time", "Failure test", M), ("INT-02", "Retries", "Three, with backoff", "Job test", M),
        ("INT-03", "Expired consent", "Reconnect banner for the user", "Manual test", S_), ("INT-04", "Zoho import", "Safe to re-run", "Import test", S_)]),
]


def fn(pages):
    d = AmperaDoc("WorkHub Non-Functional\nSpecification Document", "AMP_WH_NFSD_001", "0.1", "12-Nov-2026", "WorkHub (working name)",
                  cover_lines=["WORKHUB NON-FUNCTIONAL SPECIFICATION DOCUMENT"])
    d.toc()
    d.doc_info([("Prepared By", "Jim, Janagan, Jayasree"), ("Reviewed By", "To be assigned (Compliance)"), ("Approved By", "To be assigned"),
                ("Status", "Draft for review"), ("Audience", "Engineers, security, compliance, delivery head")])
    d.h("2. How to Read This Document", 1)
    d.callout("Draft with proposed targets",
              "Every target is a proposal for the team to confirm. Items marked TBD need an owner outside the team (HR, Compliance, IT). Priorities are Must (needed by Dec 24) and Should (if capacity allows).",
              color="A82080", fill="F8EAF4")
    d.h("2.1 Linked documents", 2)
    d.table(["Document", "Reference"], [["Functional Specification (FSD)", "AMP_WH_FSD_001"], ["Architecture Document", "AMP_WH_ARC_001"], ["Design Document", "AMP_WH_DSN_001"],
                                         ["Sprint Plan", "AMP_WH_SPL_001"], ["Product Requirements", "AMP_WH_PRD_001"]], [3.2, 3.3], size=10)
    d.h("3. Purpose", 1)
    d.p("This document defines the non-functional requirements for WorkHub: how fast, how available, how secure and how accessible it must be. It is the companion to the FSD, which defines what the system does.")
    d.h("4. Scope", 1)
    d.p("**In scope:** the WorkHub web app, API, worker, database and file storage. **Out of scope:** the Microsoft 365 tenant and the cloud platform itself, mobile apps, and activity monitoring (not built).")
    d.h("5. Definitions", 1)
    d.table(["Term", "Meaning"], [["95th percentile", "The time within which 95 of every 100 requests finish"], ["RPO", "Recovery point objective: how much data may be lost"],
                                  ["RTO", "Recovery time objective: how long recovery may take"], ["WCAG 2.2 AA", "Web accessibility standard, level AA"],
                                  ["DPDP", "Digital Personal Data Protection Act, 2023 (India)"]], [1.8, 4.7], size=10)

    n = 6
    counts = {}
    for code, title, intro, rows in NFR:
        d.h(f"{n}. {title}", 1)
        if intro:
            d.p(intro, align="left", keep=True)
        if code == "PERF":
            d.figure(charts.budget_bar("nfsd_budget", [("Network", 250, charts.TEAL), ("API", 300, charts.NAVY), ("Database", 150, charts.LAV), ("Render", 500, charts.MAG), ("Headroom", 300, charts.LGREY)],
                                       "1,500 ms budget for the week view (a design allocation, not a measurement)"), "How the 1.5 s week-view budget is shared.", 6.3)
        d.table(["ID", "Requirement", "Target (proposed)", "Verified by", "Priority"], [list(r) for r in rows], [0.7, 1.9, 2.1, 1.2, 0.6], size=8.5)
        counts[title] = {M: sum(1 for r in rows if r[4] == M), S_: sum(1 for r in rows if r[4] == S_)}
        if code == "SEC":
            d.figure(D("access"), "Access flow that the security requirements protect.", 3.9)
        if code == "AVL":
            d.figure(D("deployment"), "Target deployment: two API replicas, one worker, managed data zone.", 6.3)
        n += 1

    d.h(f"{n}. Summary and Traceability", 1)
    cats = list(counts)
    p = charts.stacked("nfsd_counts", cats, [("Must", [counts[c][M] for c in cats]), ("Should", [counts[c][S_] for c in cats])], [charts.NAVY, charts.LAV], "Requirements", figsize=(7.2, 3.8))
    total = sum(sum(v.values()) for v in counts.values())
    d.figure(p, f"Non-functional requirements by category and priority ({total} in total).", 6.0)
    d.table(["Requirement area", "Realised by"],
            [["Performance and capacity", "WH-20, WH-21 (rules), WH-90 (end-to-end journeys), WH-94 (load test at release)"], ["Security and privacy", "WH-04, WH-06, WH-50, WH-51, WH-91"],
             ["Accessibility", "WH-05, WH-93"], ["Operations", "WH-07, WH-92, WH-94"]], [2.5, 4.0], size=10)
    d.closing(n + 1, "Jim, Janagan, Jayasree", "Initial draft of the WorkHub non-functional specification.")
    return d


if __name__ == "__main__":
    pdf, n_, missing = render.build(fn, OUT)
    print(pdf, n_, "pages; headings without page:", missing)
    render.contact(pdf, os.path.join(H, "_ref", "nfsd.png"), 0, 18, 6, 40)
