# Zoho Projects / People / Payroll: pricing and feature-by-plan matrix

Researched 2026-11-12. Prices exclude GST/VAT/local taxes. "Annual" means the per-month price when billed yearly.

**How the prices were obtained.** Zoho's pricing pages load their numbers with JavaScript, so WebFetch and plain HTML show blank price cells. The pages read every currency from public JSON files on Zoho's own CDN (`zohowebstatic.com/sites/zweb/json/pricing/<product>-pricing-val.json`). Each entry in those files is stored as `monthly//yearly`, one value per currency. The figures below come from those files, matched to the plan IDs used in the page HTML, and were cross-checked against third-party listings where any existed. Zoho Payroll prices are server-rendered and were read straight off the pages.

**Pages that failed to load (HTTP 404):**
- `zoho.com/in/projects/pricing.html`
- `zoho.com/people/pricing.html`
- `zoho.com/in/people/pricing.html`
- `zoho.com/in/one/pricing/`
- `zoho.com/one/applications.html`

Projects and People have no separate `/in/` page. India sees the same global page with an INR toggle. Payroll is the only one of the three with separate India and US editions.

Source keys such as [P1] refer to the Sources list at the end.

---

## 1. Price tables

### 1a. Zoho Projects (per user per month)

| Plan | USD monthly | USD annual | INR monthly | INR annual | Users / projects / storage |
|---|---|---|---|---|---|
| Free | $0 | $0 | ₹0 | ₹0 | Up to 5 users, 3 projects, 5 GB [P1][P2] |
| Premium | $5 | $4 | ₹350 | ₹280 | Unlimited projects, 100 GB, 20 templates [P2][PJ] |
| Enterprise | $10 | $9 | ₹700 | ₹630 | Unlimited projects, 120 GB, 30 templates [P2][PJ] |
| Ultimate | $15 | $14 | ₹1,050 | ₹980 | 15 GB per user (minimum 150 GB per org), 50 templates [P1][PJ] |

Notes:
- **Free plan project count conflicts.** The pricing card and the comparison grid both say 3 projects. The FAQ on the same page says a downgrade to Free leaves "two projects" [P1].
- **No minimum user count** is shown for any paid plan [P1].
- **Discounts and quotes.** The page says yearly billing saves "over 15%" [P1]. Organizations with more than 5,000 users get a custom quote [P2].
- **Add-ons** [P2][PJ]:
  - Client users: $5 monthly / $4 annual per client user (₹350 / ₹280). Available on Premium and above.
  - Read-only users: $10 monthly / $7 annual per 5 users (₹700 / ₹490). Enterprise and Ultimate. Enterprise includes 10 and Ultimate includes 100.
  - Resources: same price as read-only users. Enterprise add-on; Ultimate includes 100.
  - Lite users: $5 / $4 (₹350 / ₹280). Ultimate only.
- **Cross-check.** Capterra and tech.co list the same annual prices: $4 / $9 / $14 [T1][T2].

### 1b. Zoho People (per user per month)

Zoho runs two different plan sets. US visitors see a US-only set; everyone else, including India, sees the global set. In the JSON, the US plan IDs have USD values only [HJ][H2].

**Global and India set:**

| Plan | USD monthly | USD annual | INR monthly | INR annual |
|---|---|---|---|---|
| Free | $0 | $0 | ₹0 | ₹0 |
| Essential HR | $1.50 | $1.25 | ₹60 | ₹48 |
| Professional | $2.50 | $2.00 | ₹120 | ₹96 |
| Premium | $3.50 | $3.00 | ₹180 | ₹144 |
| Enterprise | $5.00 | $4.50 | ₹240 | ₹192 |

- Free covers up to 5 users, with 250 MB storage and 1 administrator [H2][H1].
- Paid plans have a **minimum of 5 users** [H1].
- Paid storage per 100 users: Essential HR 1 GB, Professional 2 GB, Premium 3 GB, Enterprise 5 GB [H2].

**US-only set:**

| Plan | USD monthly | USD annual |
|---|---|---|
| Free | $0 | $0 |
| Essential HR | $4 | $3 |
| Workforce | $6 | $5 |
| Talent | $6 | $5 |
| Enterprise | $10 | $8 |

- Free covers up to 3 users [H2].
- Source for the prices: [HJ], plan IDs `zplan-core-HR`, `zplan-time-attendance`, `zplan-talent-management` and `zplan-us-enterprise`. A third-party post lists the same figures [T3].
- Other notes: yearly billing saves "more than 20%" [H1]. Organizations with more than 500 users get a custom quote [H1]. Licenses count active users only [H1].

### 1c. Zoho Payroll

Pricing is **per organization plus per employee**, not per user.

**India (INR, per org per month)** [Y1][Y2]:

| Plan | Monthly | Annual | Employees included | Each extra employee (monthly / annual) |
|---|---|---|---|---|
| Free | ₹0 | ₹0 | Up to 10 (free forever) | n/a |
| Standard | ₹1,250 | ₹1,000 | 25 | ₹50 / ₹40 |
| Professional | ₹3,750 | ₹3,000 | 50 | ₹75 / ₹60 |
| Premium | ₹5,000 | ₹4,000 | 50 | ₹100 / ₹80 |

- Each legal entity needs its own license. One entity with several branches needs only one [Y1].
- The trial lasts 14 days [Y1].

**US (USD)** [Y3]:

| Plan | Monthly | Annual | Per employee (monthly / annual) | Scope |
|---|---|---|---|---|
| Standard | $39/org | $29/org | +$6 / +$5 | Single-state payroll, any of the 50 states |
| Professional | $59/org | $49/org | +$8.50 / +$7 | Multi-state payroll |

- **There is no US free plan**, only a 14-day trial [Y3].
- Post-paid fees [Y3]:
  - Next-day processing: $3 per employee
  - W-2 postal delivery: $3 per employee
  - Wire transfer: $10
  - Amended return: $150
  - Delayed filing: $150
  - Employer fund transfer failure: $100
  - Failed employee payment: $8

### 1d. Bundles

| Bundle | USD monthly | USD annual | INR monthly | INR annual | Includes P / Pe / Pay? |
|---|---|---|---|---|---|
| Zoho One, All-Employee (every employee must be licensed) | $45 | $37 | ₹2,500 | ₹1,250 | Projects ✓, People ✓, Payroll ✓ [O1][O2][Y1][Y3] |
| Zoho One, Flexible User | $105 | $90 | ₹4,000 | ₹3,500 | Same as All-Employee |
| People Plus Premium (global) | $4.50 | $4.00 | ₹240 | ₹192 | People + Payroll Standard + Recruit Standard + Cliq Free [PP][PPJ]. **No Projects** |
| People Plus Enterprise (global) | $10 | $9 | ₹450 | ₹350 | People Enterprise + Payroll Professional + Recruit + Expense + Connect + Cliq + Vault [PP][PPJ]. **No Projects** |
| People Plus Premium (US) | $10 | $8 | n/a | n/a | US price set [PPJ] |
| People Plus Enterprise (US) | $15 | $12 | n/a | n/a | US price set [PPJ] |
| Zoho Workplace Standard / Professional | $4 / $7 | $3 / $6 | ₹129 / ₹489 | ₹99 / ₹399 | **None.** Workplace is mail, WorkDrive, Cliq and Meeting [W1][WJ] |

Bundle notes:
- **Zoho One prices** are per user or employee per month [OJ].
  - The live page shows "US$37 … First year only" for All-Employee and US$90 for Flexible [O1].
  - The JSON also holds unexplained US-only entries of $30 and $67 [OJ]. I could not confirm what they are.
  - Third-party Indian resellers quote ₹1,250 to ₹1,500 for All-Employee and ₹3,500 for Flexible [T4].
- **Payroll inside Zoho One.** The US Payroll FAQ says Zoho One includes Payroll **Standard** only: single-state, with no multi-state or pay-run approvals [Y3]. The India FAQ says Payroll is included but gives no edition [Y1].
- **People Plus** has a 5-user minimum [PP]. Its "Plan includes" list (People Premium Workforce, Payroll Standard) was the version rendered for India; the US Payroll edition inside US People Plus was not confirmed.
- **Projects Plus** (Projects + Sprints + Analytics + WorkDrive + Notebook + Learn) is "Contact us" on the page [P1]. The JSON holds $16 monthly / $15 annual and ₹1,120 / ₹1,040, but the page does not show these prices.

**Are the three products cheaper bundled?** No, unless you would actually use the other apps. Example for 25 users on annual billing, buying the lowest plans that include leave, attendance, timesheets and payroll:

| Option | India (₹/month) | US ($/month) |
|---|---|---|
| Standalone: Projects Premium + People (IN: Professional / US: Workforce) + Payroll Standard | 7,000 + 2,400 + 1,000 = **₹10,400** | 100 + 125 + (29 + 125) = **$379** |
| People Plus Enterprise + Projects Premium | 8,750 + 7,000 = ₹15,750 | (25 × $12) + 100 = $400 |
| Zoho One All-Employee | 25 × 1,250 = ₹31,250 | 25 × 37 = $925 |
| Zoho One Flexible | 25 × 3,500 = ₹87,500 | 25 × 90 = $2,250 |

Zoho One costs about 3x the standalone stack for these three products alone. It only pays off once you would otherwise buy CRM, Books, Desk and so on. People Plus wins only if you also need Recruit and Expense.

---

## 2. Combined feature × plan matrix

Legend: ✓ = included, ✗ = not included, text = limit, n/l = not listed on the comparison page.

Column keys:
- **Projects** [P1][P2]: PF = Free, PP = Premium, PE = Enterprise, PU = Ultimate.
- **People, global/India** [H1][H2]: HF = Free, HE = Essential HR, HP = Professional, HPr = Premium, HEn = Enterprise.
- **People, US** [H2]: UE = Essential HR, UW = Workforce, UT = Talent, UEn = Enterprise. The US Free plan has time off only.
- **Payroll, India** [Y1][Y2]: YF = Free, YS = Standard, YP = Professional, YPr = Premium.
- **Payroll, US** [Y3]: US = Standard, UP = Professional.

| Feature | PF | PP | PE | PU | HF | HE | HP | HPr | HEn | UE | UW | UT | UEn | YF | YS | YP | YPr | US | UP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Timesheets / time logs | ✗ | ✓ | ✓ | ✓ multi-user, multi-project | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | – | – | – | – | – | – |
| Timesheet approval | ✗ | ✓ multi-level + approval rules | ✓ | ✓ | ✗ | ✗ | ✓ (scheduler auto-submits) | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | – | – | – | – | – | – |
| Billable hours / billing | n/l¹ | n/l¹ | n/l¹ | n/l¹ | ✗ | ✗ | ✓ billing & invoicing | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | – | – | – | – | – | – |
| Project budget / EVM | ✗ | ✓ | ✓ | ✓ | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Gantt chart | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Task dependencies | Finish-to-start, within project | All 4 types, within project | All 4 types, across projects | All 4 types, across projects | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Critical path / baselines | ✗ | ✗ | ✓ / 15 per project | ✓ / 15 per project | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Blueprints | ✗ | 2 per layout | 25 per layout | 50 per layout | ✗ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | n/l | n/l | n/l | n/l | n/l | n/l |
| Workflow rules | 2 per layout | 2 per layout | 20 per layout | 40 per layout | ✗ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | n/l | n/l |
| Automation actions per month | 50 | 500 (grid) or 5,000 (card)² | 50,000 | 500,000 | webhooks only | ✓ | ✓ | ✓ | ✓ | webhooks only | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ functions + schedulers | n/l | n/l |
| Custom fields | ✗ | Custom-module fields only (52) | ✓ (265 task fields) | ✓ | ✗ | 1 form per 10 users | 2 forms per 10 users | 3 forms per 10 users | 5 forms per 10 users | 1 per 10 | 2 per 10 | 3 per 10 | 5 per 10 | ✗ | ✗ | ✓ | ✓ + custom modules | ✗ | ✓ |
| Custom layouts | View only | ✓ | ✓ | ✓ | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | – | – | – | – | – | – |
| Custom roles / profiles | ✗ | ✗ | ✓ | ✓ | n/l (1 admin on Free) | n/l (unlimited admins) | n/l | n/l | n/l | n/l | n/l | n/l | n/l | Predefined only | Predefined (card); grid says custom³ | ✓ custom | ✓ | ✗ | ✓ |
| Client users | ✗ | Add-on | Add-on | Add-on | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Read-only users | ✗ | ✗ | 10 | 100 | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Reports | 1 predefined report per module | 20 per module | 50 per module | 250 per module | Standard | Standard + Analytics | Standard + Analytics | + custom | + custom | ✗ (Free) | Standard + custom | Standard + custom | Standard + custom | 40+ built-in | ✓ | ✓ + reporting tags | ✓ | Auto-generated | + reporting tags |
| Dashboards (project / global) | 1 / 1 | 5 / 1 | 10 / 5 + portfolio | Unlimited | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l |
| Integrations | Google, Office 365, Slack, Teams, CRM, Zapier | + Zoho People, Books, Invoice, Analytics, Flow, GitHub | + Desk, Power BI, Directory | + DAP | E-sign, webhooks | + Vault, Analytics | + FTP / biometrics | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | Books, People, Expense | + ICICI, WhatsApp | ✓ | + webhooks | Accounting, Expense | ✓ |
| Issue tracker | Basic issues | + email-to-issue, business rules, web form | + SLA, custom fields, link issues⁴, webhooks | ✓ | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| Leave management | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ✓ (+ Bradford score) | **✗** | ✓ | **✗** | ✓ | ✗ | ✗ | ✗ | ✓ | PTO ✓ | PTO ✓ |
| Leave approval workflow | – | – | – | – | ✓ (time-off approvals) | ✓ multi-level | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ (manager approves in portal) | n/l | n/l |
| Attendance | – | – | – | – | ✗ | ✗ | ✓ web, mobile, face, biometric, geo/IP | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Shifts | – | – | – | – | ✗ | Create, schedule, change requests | + rotation, patterns, reminders | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | n/l | ✗ | ✗ |
| Holiday calendar | ✗ | 1 calendar + holiday list | 3 | 20 | ✓ | ✓ | ✓ | ✓ | ✓ | n/l | ✓ | n/l | ✓ | n/l | n/l | n/l | n/l | n/l | n/l |
| Payslips | – | – | – | – | – | – | – | – | – | – | – | – | – | ✓ + templates | ✓ | ✓ | ✓ | n/l⁵ | n/l⁵ |
| Tax declarations / proofs | – | – | – | – | – | – | – | – | – | – | – | – | – | ✓ IT declaration + POI | + Form 16 signer, TDS challan | ✓ | ✓ | ✓ federal, state, local filing | ✓ |
| Reimbursements | – | – | – | – | – | – | – | – | – | – | – | – | – | ✓ proof approval | ✓ | ✓ | ✓ | Expense integration | ✓ |
| Employee self-service portal | – | – | – | – | ✓ | ✓ | ✓ | ✓ | ✓ | n/l | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ web + mobile | ✓ |
| Mobile apps | ✓ iOS + Android | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/l | n/l | n/l | n/l | ESS app, plan not stated | ESS app | ESS app | ESS app | ✓ | ✓ |
| Audit logs | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | **✗** | ✓ audit trail | ✓ | ✓ | n/l | n/l |
| Notifications / alerts | Email templates + alerts; feeds | + issue notifications, reminders | ✓ | ✓ | n/l | Mail alerts | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | Predefined email alerts + reminders | ✓ | + custom alerts and reminders | ✓ | n/l | n/l |
| SSO / 2FA | ✗ | ✗ | ✓ | ✓ | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | n/l | MFA, all plans | ✓ | ✓ | ✓ | n/l | n/l |
| Sandbox | ✗ | ✗ | 1 | 10 | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ | – | – | – | – | – | – |

Footnotes:
1. Zoho's Projects pricing and comparison pages do not list billable or non-billable hours. Help-forum and third-party sources say the billable/non-billable flag comes with time logs, so in practice Premium and above [T5].
2. The pricing card says Premium gets 5,000 automation executions per month [P1]. The full comparison grid says 500 [P2].
3. The India Payroll pricing card puts customisable roles on Professional and predefined roles on Standard [Y1]. The comparison grid shows custom roles from Standard [Y2]. The two also disagree on Loans: the card says Standard and above, the grid shows Free.
4. "Link Issues" is Premium and above on the summary grid [P1] but Enterprise and above on the full comparison [P2].
5. US pay stubs are not named on the US pricing page. Its employee self-service portal is listed on Standard [Y3].

---

## 3. Notable gating gotchas

1. **Projects Free has no time tracking.** Timesheets, approvals, budgets, recurring tasks and business-hours/holiday calendars all start at Premium [P2].
2. **Projects custom fields and custom roles/profiles are Enterprise and above.** Premium gets custom views and statuses but no task, issue or project custom fields, and no custom roles [P1][P2]. Fine-grained client permissions, SSO, 2FA, critical path, baselines, cross-project dependencies and Power BI are also Enterprise and above [P1].
3. **Multi-user, multi-project timesheets are Ultimate only**, and so are unlimited dashboards. Premium gets 1 global dashboard [P1][P2].
4. **Client users are a paid add-on on every Projects plan**: $5 / $4 (₹350 / ₹280) per client user [P2][PJ].
5. **People attendance, timesheets and shift rotation start at Professional (global) or Workforce (US).** Essential HR gives leave and basic shifts only [H2].
6. **US Zoho People: Essential HR and Talent have no time-off or leave module at all** (marked "-" in the grid). Only Free, Workforce and Enterprise include it, so a US buyer needing leave plus performance reviews must buy Enterprise [H2].
7. **People custom reports are Premium and above (global).** Data backup, Bradford score, personal file uploads, the HR help desk, LMS and sandbox are Enterprise only [H2].
8. **India Payroll's leave and attendance, workflow rules, webhooks and custom functions are Premium only.** In the employee portal, leave apply/approve and attendance marking are Premium only [Y1][Y2].
9. **India Payroll has no audit trail on Free.** It starts at Standard [Y1]. Pay-run and salary-revision approvals start at Professional [Y2].
10. **US Payroll Standard is single-state only.** Multi-state payroll, pay-run approvals, custom roles and custom fields need Professional [Y3]. **Zoho One includes only Payroll Standard (US)** [Y3].
11. **Zoho Workplace includes none of the three products** [W1]. People Plus bundles People + Payroll but **not** Projects [PP].

---

## 4. Sources

Official Zoho sources:
- [P1] https://www.zoho.com/projects/pricing.html (redirects to https://www.zoho.com/projects/zohoprojects-pricing.html)
- [P2] https://www.zoho.com/projects/pricing-comparison.html
- [PJ] https://www.zohowebstatic.com/sites/zweb/json/pricing/projects-pricing-val.json (Zoho's own price data, loaded by P1/P2; layout `monthly//yearly`, currency order USD;OLDUSD;INR…)
- [H1] https://www.zoho.com/people/zohopeople-pricing.html
- [H2] https://www.zoho.com/people/pricing-comparison.html (global grid, then a US grid)
- [HJ] https://www.zohowebstatic.com/sites/zweb/json/pricing/people-pricing-val.json
- [PP] https://www.zoho.com/peopleplus/pricing.html
- [PPJ] https://www.zohowebstatic.com/sites/zweb/json/pricing/peopleplus-pricing-val.json
- [Y1] https://www.zoho.com/in/payroll/pricing/
- [Y2] https://www.zoho.com/in/payroll/pricing-comparison/
- [Y3] https://www.zoho.com/us/payroll/pricing/
- [O1] https://www.zoho.com/one/pricing/ (geo-variant page: served a LATAM/US variant, Essentials price not shown)
- [OJ] https://www.zohowebstatic.com/sites/zweb/json/pricing/one-pricing-val.json
- [O2] https://www.zoho.com/one/plan-details.html (lists Projects, People and Payroll as Zoho One apps)
- [W1] https://www.zoho.com/workplace/pricing.html (redirected to /en-in/)
- [WJ] https://www.zohowebstatic.com/sites/zweb/json/pricing/workplace-pricing-val.json

Third-party sources, used for cross-checks only:
- [T1] https://www.capterra.com/p/169455/Zoho-Projects/
- [T2] https://tech.co/project-management-software/zoho-projects-pricing-review
- [T3] https://www.noon.ai/blog/articles/437-zoho-people-pricing-2026
- [T4] https://codroiditlabs.com/zoho-one-pricing-review/ and https://www.capterra.in/software/166175/zoho-one
- [T5] https://help.zoho.com/portal/en/community/topic/timesheets-2-8-2016

Failed with HTTP 404: zoho.com/in/projects/pricing.html, zoho.com/people/pricing.html, zoho.com/in/people/pricing.html, zoho.com/in/one/pricing/, zoho.com/one/applications.html.
