# Zoho Projects / People / Payroll: User Pain Points

Research date: 2026-11-12. Web only, read-only. 34 distinct search queries plus 16 page fetches.

## Method and caveats

- **Coverage gaps:** Reddit and Quora were not reachable. The search tool rejects `reddit.com` as a domain filter, WebFetch is blocked on reddit, and no Quora threads came up in results. G2, Capterra, TrustRadius and Software Advice return HTTP 403 on direct fetch, so their content comes from search-result snippets and aggregator summaries, not full reads. SoftwareSuggest, the Zoho community forums, Zoho help docs, the Play Store (via search) and comparison blogs were read directly.
- **Counting:** "Sources" counts distinct pages or threads that raise the issue, not individual reviewers. A review-site page that mentions an issue in several reviews counts once, with the reviewer count in brackets where known.
- **Bias:** Many "alternatives" blogs (Upbase, Thrivea, Lark, Leave Balance, Keka, Tallyfy) are written by competitors. They are used only to corroborate, and are marked *(vendor)*.
- **Age:** Many Zoho community threads are old and unanswered. "Unresolved" below means no fix was visible on the page, not that none exists today.

Personas: **Mgr** = Manager / approver, **HR**, **Emp** = Employee, **AF** = Admin-Finance.

---

## 1. Top 15 pain points (ranked by number of sources)

| # | Pain point | Module | Personas | Sources | Verdict on candidate theme |
|---|---|---|---|---|---|
| 1 | Mobile apps lag behind the web: crashes, timers that won't stop, no timer on team tasks, missing timesheet templates, regularization hard to reach, no employer payroll app | Cross-cutting: mobile (Timesheets, Attendance) | Emp, Mgr | 11 | **Confirmed** (poor mobile app) |
| 2 | Cluttered UI, steep learning curve, setup needs training | Cross-cutting: UI | All | 10 | **Confirmed** (UI clutter, learning curve) |
| 3 | Zoho apps don't integrate cleanly with each other: timesheets sync one way only, partial pushes, Payroll ignores People leave unless modules are disabled, cross-org bank conflicts | Cross-cutting: integrations | AF, HR, Mgr | 10 | **Confirmed** (integration gaps between Zoho apps) |
| 4 | Pricing creep and tier gating: features locked to top plans, People Premium doubled in July 2026, separate bills per app, plan caps force upgrades | Cross-cutting: pricing | AF | 9 | **Confirmed** (pricing creep) |
| 5 | Support is slow or can't resolve issues, especially below premium tiers; escalations stall for months | Cross-cutting: support | AF, HR | 8 | **Confirmed** |
| 6 | Notifications go both ways wrong: Projects floods inboxes and ignores opt-outs, while leave and timesheet events silently fail to notify | Cross-cutting: notifications | Mgr, Emp | 8 (3 overload, 5 gaps) | **Confirmed, both directions** |
| 7 | Built-in reporting is shallow; custom reports need Zoho Analytics (another app, a sync step, more cost) | Cross-cutting: reporting | Mgr, HR, AF | 7 | **Confirmed** |
| 8 | Slow loading and hangs | Cross-cutting: UI | All | 6 | **Confirmed**, mostly Projects |
| 9 | Leave approval friction: unapproved leave counted as paid or indistinguishable in attendance, approver access errors, no bulk approve, PTO policy setup errors | Leave | Mgr, HR | 6 | **Confirmed** |
| 10 | Timesheet friction: people forget to log, reminders are admin-only config, rejected logs don't notify the employee, entry is tedious, hours go missing across time zones | Timesheets | Emp, Mgr | 6 | **Partly confirmed.** Reminders exist but must be set up by an admin. Rejection feedback is the real gap. |
| 11 | Roles vs profiles vs permission sets is confusing, custom profiles are plan-gated, and odd access errors appear | Cross-cutting: permissions | Admin, Mgr | 5 | **Confirmed** (moderate) |
| 12 | Geo/photo attendance check-in fails or picks the wrong location; regularization computes wrong hours | Attendance | Emp, HR | 5 | **Confirmed** (not in the candidate list) |
| 13 | Customization limits: templates, salary components, leave/performance forms | Cross-cutting | HR, AF | 5 | **Confirmed** |
| 14 | Payroll rigidity: can't edit one employee after a pay run, mid-cycle joiners wait a month, wrong paid days on payslip, can't add some deductions | Payroll | AF, Emp | 4 | **Confirmed** (low volume, high severity) |
| 15 | Leave↔timesheet and leave↔calendar disconnect: cancelled leave stays on Google Calendar, hourly leave shows wrong times, only one calendar provider, People leave reaches Projects only if configured per resource | Leave / Timesheets | Emp, Mgr | 4 | **Confirmed** (leave↔timesheet disconnect) |

Lower-volume but notable: no per-task change history, and the audit log is visible to the portal owner only (3 sources). Payslip bulk download, and access after an employee leaves (2). Approval delegation exists but users can't easily reroute *pending* items (2).

---

## 2. Pain points by persona

### Manager / approver
- **Notification overload in Projects:** every small change emails the team and even clients, and unchecking the box doesn't stop it. Sources: community "turn off auto-email", Capterra snippet "notification overload", community tips threads (3).
- **Missed approval alerts:** some leave requests never email the approver. Alerts are email-only (a Cliq channel was requested), and the email omits the approver name and number of days (4).
- **Approver blocked:** an approver trying to approve a subordinate's leave got a "not allowed to access this data" error. Approvers were also switched to the portal admin without anyone asking (2).
- **No bulk approval** for imported or pending leave. Approvals are handled one by one in Payroll (2).
- **Unapproved leave is hard to tell apart** in the attendance view, especially hourly leave (1). Unapproved leave was counted as paid in attendance (1).
- **Delegation:** a delegation feature exists, but users ask how to reroute approvals that are *already pending* when a manager goes on leave (2).
- **Reporting:** dashboards are sub-optimal, the Projects reporting module can't create new reports, and filters are weaker than Jira's JQL for cross-project views (4).
- **Mobile:** can't stop a running timer, no timer on team tasks, templates missing (4).

### Employee
- **Attendance check-in fails:** geo check-in fails at the correct office even after 10+ retries, the wrong location gets selected, photo check-in gives no clear feedback, and checkout broke after an update (Play Store, TrustRadius, G2, SoftwareSuggest: 4).
- **Regularization:** hard to find on mobile, and it calculates wrong total hours for past dates (3).
- **Timesheets:** easy to forget to log (Zoho's own sticky post admits this). Entry is tedious because project and milestone must be picked every time. Rejected logs don't notify the employee. Hours go missing across time zones (4).
- **Mobile parity:** timesheet editing and some reports require switching to the web (Thrivea, Software Advice, G2: 3).
- **Payslips:** a payslip showed 31 paid days in April. The annual CTC breakup appears only in the PDF. Bank details are masked with no reveal. No easy way to download all payslips, especially after the account is disabled (3).
- **Leave calendar:** a cancelled leave isn't removed from the shared Google Calendar, hourly leave shows wrong times across time zones, and leave can sync to Google or Outlook but not both (2 threads + docs).

### HR
- **Setup complexity:** PTO policies are hard to configure correctly and lead to admin overrides. The setup guide is outdated. Initial configuration is complex (5).
- **Customization limits** on leave, performance, and forms. Extra custom forms and storage are paid add-ons (3).
- **Payroll link fragility:** to integrate Payroll with People, the Leave and Attendance module in Payroll must be disabled, and it can't be re-enabled. Pay period and cut-off dates must line up, or LOP doesn't flow. Regional docs contradict each other on whether leave syncs at all (Zoho docs: 2).
- **Integrations outside Zoho** are weak: no Gusto/Patriot payroll connectors, and Slack/Teams can't do in-chat leave requests and approvals (2).
- **Biometric sync** breaks on network changes and needs device-ID mapping (1, vendor).
- **Missing features:** work-from-home monitoring, break tracking, half-day leave, holiday-work handling (2).

### Admin / Finance
- **Price creep:** People Plus Premium went from $4 to $8 per user per month (annual billing) and Enterprise from $9 to $12, detected July 2026. There is a big Premium-to-Enterprise jump in Projects, the Basic plan used for timesheet-only users is being phased out, and one Zoho One customer is leaving over a bill above $6k a year (6).
- **Separate apps mean separate seats:** a bookkeeper who runs payroll needs a paid seat despite not being on payroll, and Zoho said this is by design (1).
- **Payroll rigidity:** no single-employee correction after a pay run (the whole run must be reversed), mid-month joiners wait for the next cycle, Professional Tax can't be added as a deduction, a rejected salary revision can't be deleted, there's no bonus-act calculation, and no multi-level payroll approval (SoftwareSuggest, Capterra, G2 snippets: 3).
- **Bank integration:** ICICI only. A bank account linked in one Zoho org can't be used in another. One issue stayed open for 3+ months (1 page, 3 reviewers).
- **Support:** tickets get forwarded to engineering with no fix, one reviewer rated support 0/5, there's no phone or live chat without premium, and community threads complain of months without a reply (8).
- **Data:** the leave API can't filter by approval status and doesn't return leave type, which blocks payroll integrations (1). Only the portal owner can see the audit log (1). An EU vs .com data-center split blocked client access (1).

---

## 3. Wished-for and small missing features

Each item is something a user asked for or noted as missing. Source count in brackets.

**Approvals (leave and timesheets)**
- Bulk approve or reject for leave and imported records [2]
- Reroute already-pending approvals to a delegate, and auto-delegate while the approver is on leave [2]
- Notify the employee immediately when a time log is rejected, with the reason shown [1]
- Approval emails that include the approver name, leave days, and reason [1]
- Grey-out or label unapproved leave in attendance views [1]
- Notifications beyond email (Cliq/Slack/Teams), with approve-in-chat [2]
- Multi-level payroll approval [1]

**Timesheets**
- Reminders employees can't miss, on by default rather than admin-configured [2]
- Two-way sync between Projects time logs and People timesheets, so payroll gets one consolidated report per person [3]
- A mobile timer for team-assigned tasks, and timesheet templates on mobile [2]
- Faster bulk entry: remember the last project or milestone, log multiple tasks at once [1]

**Leave and attendance**
- Approved leave shows automatically in project capacity and timesheets [2]
- Calendar sync that removes cancelled leave, handles time zones, and supports both Google and Outlook [3]
- Half-day leave, holiday-work handling, break tracking, WFH tracking [2]
- Reliable geo check-in with clear success or failure feedback [4]

**Payroll and payslips**
- Bulk payslip download per employee, plus access after exit [2]
- Annual CTC breakup on screen, not just in the PDF [1]
- Correct a single employee after a pay run without reversing the whole run [1]
- Mid-cycle joiner handling and custom salary components (phone allowance, Professional Tax) [2]

**Cross-cutting**
- Per-task change history ("who deleted this task") visible to managers, not only the portal owner [3]
- Custom reports inside the product, without Zoho Analytics [4]
- Notification controls that actually work, plus digest mode [3]
- One price for one suite, instead of per-app seats [3]

---

## 4. Opportunities for the replacement

1. **One data model for person, project, time, leave and pay.** Approved leave should block capacity in Projects, pre-fill timesheet days as leave, and feed LOP straight into payroll with no sync job, cut-off dates or module toggles. This fixes pain points #3 and #15, the most structural complaints.
2. **Approval inbox done right.** One queue for leave, timesheets and regularization. Bulk approve and reject. A required or optional reason that the requester sees in the UI. A full approval trail (who approved, when, and any comment). Delegation with auto-reroute of pending items while the approver is on leave. Approve from email or chat.
3. **Notification defaults that respect people.** In-app first, a daily digest, per-event opt-out that's honored, and *never* missing the critical ones (approval requested, approved, rejected). Both overload and silence are real complaints.
4. **Timesheet nudges by default.** Automatic reminders for missing days, skipping days on approved leave. Remember the last project and task. Week-grid entry. Rejection sends the employee back to the exact entry.
5. **Mobile parity on the three daily jobs:** check-in/out, log time, and apply for or approve leave. Clear check-in feedback and a fallback when GPS fails.
6. **Simple permissions:** a few roles (Employee, Manager, HR, Finance, Admin) scoped by reporting line and project membership, with no separate "profile vs role" concepts. Plus "why can't I see this?" messages.
7. **Built-in reports that cover the 80% case:** utilization, timesheet compliance, leave balances, payroll register, all exportable to CSV with no second analytics product.
8. **Audit history everywhere,** visible to managers for their own scope.
9. **Payroll flexibility:** correct one employee after a pay run, prorate mid-cycle joiners, custom earnings and deductions, an annual breakup on the payslip screen, and bulk or historical payslip download that keeps working after exit.
10. **Being internal is itself the pricing and support win.** No per-app seats, tier gates or vendor tickets. Keep the UI uncluttered and fast, because slowness and clutter rank #2 and #8.

---

## 5. Sources

**Zoho community forums and help docs**
- https://help.zoho.com/portal/en/community/topic/absolutely-need-to-turn-off-auto-email-notifications
- https://help.zoho.com/portal/en/community/topic/tip-8-know-your-email-notification-settings-better
- https://help.zoho.com/portal/en/community/topic/tip-31-control-your-email-notifications?page=13
- https://help.zoho.com/portal/en/community/topic/zoho-people-leave-api-limitation
- https://help.zoho.com/portal/en/community/topic/leave-application-approver-settings-in-zoho-people
- https://help.zoho.com/portal/en/community/topic/zoho-people-leave-application
- https://help.zoho.com/portal/en/community/topic/approver-not-able-to-approve-leave-request
- https://help.zoho.com/portal/en/community/topic/unapproved-leaves-are-hard-to-distinguish-in-attendance-view
- https://help.zoho.com/portal/en/community/topic/leave-approval-send-confirmation-emails-to-requester-and-additional-users?page=7
- https://help.zoho.com/portal/en/community/topic/send-zoho-people-manager-notifications-via-zoho-cliq?page=2
- https://help.zoho.com/portal/en/community/topic/delegation-option-for-approval
- https://help.zoho.com/portal/en/kb/people/administrator-guide/operations/employee-information/articles/delegations-management-zoho-people
- https://help.zoho.com/portal/en/kb/people/administrator-guide/settings/employee-information/articles/dual-reporting
- https://help.zoho.com/portal/ar/community/topic/automatic-approval-of-leave-time?page=62
- https://help.zoho.com/portal/en/community/topic/time-log-reminder
- https://help.zoho.com/portal/en/kb/projects/settings-in-zoho-projects/automation/timesheet-automation/articles/approval-rules-for-timesheet-1-6-2025
- https://help.zoho.com/portal/en/community/topic/timesheet-rejection-notification
- https://help.zoho.com/portal/en/community/topic/timesheet-adding-incorrectly-missing-hours-timezone-ch
- https://help.zoho.com/portal/en/community/topic/integrate-timesheets-from-projects-and-support-into-people
- https://help.zoho.com/portal/en/community/topic/zoho-people-timesheet-sync-to-zoho-projects
- https://help.zoho.com/portal/en/community/topic/zoho-projects-integration-with-zoho-people
- https://help.zoho.com/portal/en/community/topic/how-can-i-sync-or-setup-holiday-or-pto-of-users-on-zoho-projects
- https://help.zoho.com/portal/en/community/topic/syncing-leave-calendar-with-shared-google-calendar-does-not-remove-canceled-leaves
- https://help.zoho.com/portal/fr/community/topic/zoho-people-leaves-and-google-calendar-sync-wrong-times
- https://help.zoho.com/portal/en/kb/people/administrator-guide/leave/user-service/articles/user-service-leave
- https://help.zoho.com/portal/ja/community/topic/zoho-people-attendance-regularization-%e2%80%93-wrong-total-hours-displayed
- https://help.zoho.com/portal/nl/community/topic/issue-in-zoho-people-regularization-%e2%80%93-incorrect-hour-calculation?page=1
- https://help.zoho.com/portal/en/community/topic/projects-extremely-slow-and-unresponsive
- https://help.zoho.com/portal/en/community/topic/zoho-s-biggest-issue-is-unaddressed-slowness
- https://help.zoho.com/portal/ja/community/topic/zoho-project-for-crm-is-clumsy-and-not-intuitive?page=2
- https://help.zoho.com/portal/en/community/topic/cant-stop-time-tracker-on-zoho-project-mobile
- https://help.zoho.com/portal/fr/community/topic/projects-mobile-app-timer-doesnt-work-for-team-tasks?page=62
- https://help.zoho.com/portal/fr/community/topic/zoho-projects-app-timesheet-templates-not-showing-up
- https://help.zoho.com/portal/en/kb/projects/settings-in-zoho-projects/profiles-and-roles/articles/profiles-and-roles-projects
- https://help.zoho.com/portal/en/kb/projects/settings-in-zoho-projects/profiles-and-roles/articles/permission-sets-projects
- https://help.zoho.com/portal/en/community/topic/limitation-of-reports-on-zoho-projects-integration
- https://help.zoho.com/portal/en/kb/projects/integration/zoho-apps/articles/analytics-for-projects
- https://help.zoho.com/portal/en/community/topic/why-is-zoho-analytics-so-damn-hard-to-set-up
- https://help.zoho.com/portal/en/kb/projects/security-compliance-zohoprojects/articles/audit-logs-in-zoho-projects
- https://help.zoho.com/portal/en/community/topic/task-milesstone-etc-activity-tracking
- https://help.zoho.com/portal/ja/community/topic/record-project-task-status-changes-status-timeline?page=7
- https://help.zoho.com/portal/en/community/topic/poor-zoho-support?page=2
- https://help.zoho.com/portal/ja/community/topic/no-zoho-support-response-in-months?page=1
- https://help.zoho.com/portal/en/community/topic/whats-going-on-with-zoho-support
- https://help.zoho.com/portal/ja/community/topic/leaving-zoho-one-we-pay-over-6k-a-year
- https://help.zoho.com/portal/en/community/topic/so-the-basic-plan-is-being-phased-out
- https://help.zoho.com/portal/es/community/topic/unfair-price-increase-i-feel-like-trapped?page=3
- https://help.zoho.com/portal/en/community/topic/zoho-payroll-access
- https://help.zoho.com/portal/en-gb/community/topic/how-can-i-generate-a-payslip-or-salary-slip-to-email-it-to-the-employees
- https://help.zoho.com/portal/fr/community/topic/zoho-payroll-assistance-downloading-multiple-payslips
- https://help.zoho.com/portal/ja/community/topic/option-to-download-all-pay-slips-from-zoho-payroll-for-a-person-after-account-disabled
- https://help.zoho.com/portal/ja/community/topic/zoho-payroll-customer-support-not-able-to-recognize-the-problem-in-the-application
- https://help.zoho.com/portal/en/community/topic/how-to-sync-overtime-from-zoho-people-to-zoho-payroll
- https://www.zoho.com/en-bh/payroll/kb/employer/zoho-people-integration/leave-sync.html
- https://www.zoho.com/in/payroll/help/employer/integrations/integrations-people.html
- https://www.zoho.com/in/payroll/kb/employer/pay-runs/net-pay-mismatch.html
- https://www.zoho.com/in/payroll/kb/employer/employees/portal-inaccessible.html

**Review sites**
- https://www.softwaresuggest.com/zoho-payroll/reviews (fetched)
- https://www.softwaresuggest.com/zoho-people/reviews (fetched)
- https://www.softwaresuggest.com/zoho-projects/reviews (fetched)
- https://www.g2.com/products/zoho-people/reviews?qs=pros-and-cons (snippets; 403 on fetch)
- https://www.g2.com/products/zoho-payroll/reviews?qs=pros-and-cons (snippets)
- https://g2.com/products/zoho-projects/reviews?page=10 (snippets)
- https://www.capterra.com/p/169455/Zoho-Projects/reviews/ (snippets; 403 on fetch)
- https://www.capterra.com/p/110931/Zoho-People/reviews/ (snippets)
- https://www.capterra.co.uk/software/110931/zoho-people (snippets)
- https://www.capterra.com/p/186299/Zoho-Payroll/reviews/ (snippets)
- https://trustradius.com/products/zoho-people/reviews/all (snippets; 403 on fetch)
- https://www.trustradius.com/reviews/zoho-projects-2019-08-15-09-42-17 (snippets)
- https://www.softwareadvice.com/hr/zoho-people-profile/reviews/ (snippets)
- https://softwarefinder.com/hr/zoho-payroll (snippets)
- https://play.google.com/store/apps/details?id=com.zoho.people (snippets)
- https://play.google.com/store/apps/details?id=com.zoho.projects (snippets)
- https://findstack.com/products/zoho-projects/reviews?page=1

**Comparisons, alternatives and analysis** (*vendor* = competitor-authored)
- https://upbase.io/blog/best-zoho-projects-alternatives/ (fetched, *vendor*)
- https://thrivea.com/blog/zoho-people-review-2026/ (fetched, *vendor*)
- https://aaxonix.com/resources/zoho-one-limitations-honest-gap-analysis/ (fetched, Zoho partner)
- https://pricingsaas.com/companies/zoho.peopleplus/diffs/2026W29 (fetched)
- https://www.larksuite.com/en_us/blog/zoho-projects-review (*vendor*)
- https://www.techrepublic.com/article/zoho-people-review/
- https://www.leavebalance.com/blog/zoho-people-alternatives/ (*vendor*)
- https://akriviahcm.com/blog/zoho-people-alternatives-india (*vendor*)
- https://www.jibble.io/reviews/zoho (*vendor*)
- https://tallyfy.com/zoho-projects-alternative/ (*vendor*)
- https://blog.rocketlane.com/blogs/zoho-projects-alternatives (*vendor*)
- https://thedigitalprojectmanager.com/tools/zoho-projects-vs-clickup/
- https://thedigitalprojectmanager.com/tools/asana-vs-zoho-projects/
- https://www.lowcode.agency/blog/zoho-crm-support-limitations
- https://codroiditlabs.com/zoho-people-biometric-integration-after-go-live/ (*vendor*)
- https://costbench.com/software/project-management/zoho-projects/

**Not reachable:** reddit.com (blocked for both search and fetch) and Quora (no threads came up in search results).
