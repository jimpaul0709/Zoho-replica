# WorkHub UI audit: what is outdated, and what the market does

Date: 2026-11-18. Method: screenshots of the running app (signed in as the seeded HR user, light and dark) against the public sites of Zoho People, Keka, Factorial, BambooHR and Rippling. Method rules: taste-skill `redesign-skill` audit checklist, `market-research` standards (fact / inference / recommendation kept apart).

Screenshots: `docs/ui-audit/screens/` (ours) and `docs/ui-audit/competitors/` (theirs).

## 0. What I could and could not see

- Seen: sign-in, Week, Leave, Approvals, HR admin (light); Week, Leave, HR admin (dark). Payslips and Password were captured but I did not review them closely.
- Not seen: mobile width, hover and press states in motion, the Day view of Week, anything behind a competitor's login. Competitor evidence is their **marketing pages only**; their actual in-app UI is inferred from the product screenshots they publish. Ratings and customer counts below are the vendors' own claims.

## 1. The landing page does not exist (biggest gap)

Fact: `/` is the sign-in form with one pastel brand pane (`Time, leave and payslips in one place.`). No public page explains the product, shows it, or answers "what is this and why should I trust it". It is also not a place a visitor could be sent from an email or a link.

What every competitor has on their first screen (fact, from screenshots):

| Pattern | Zoho People | Keka | Factorial | BambooHR | Rippling |
|---|---|---|---|---|---|
| Top nav with product / solutions / pricing | yes | yes | yes | yes | yes |
| Two CTAs (primary + secondary like "Request demo", "Take a tour") | yes | yes | one | one | email box + button |
| Announcement bar | no | yes (summit) | no | no | no |
| Social proof directly under hero (logos, rating, customer count) | logos | logos | rating + logos, with pause | rating 4.6 (3,400+ reviews) | no |
| Product visual in the hero | below fold, floating UI cards | dashboard floating over a photo | AI prompt box with action chips | "Hi, Maya" greeting card | globe image |
| AI as the headline | "AI-first" | "AI-native" | "The AI for business" | "Bamboo AI" | no |
| Hero style | white, huge type | dark purple, huge type | white + warm gradient | dark green | dark plum |

Recommendation: build a real marketing landing at `/` and move sign-in to `/login`. Minimum sections: nav (Product, Pricing, Login, Request access), hero with one primary and one secondary CTA, a real product screenshot of the week grid, three module blocks (time, leave, payslips) in an alternating layout rather than three equal cards, a trust strip (security, audit log, SSO when Entra ID ships), and a footer with privacy and terms. Fix the copy too: `Use your Ampera email and password.` names a company the page never introduces.

## 2. Buttons and dropdowns (your hunch is right)

Facts from the screenshots:

- **Dropdowns are native `<select>` elements** (`Choose…`, `+ Add task or charge code…`, `Delegate to`, `Employee`). They show the browser's arrow, an unstyled option list, and no search. The Employee picker lists everyone as `name · email` with no search; that breaks past about 30 people.
- **Dates are native `<input type="date">`** and show `dd-mm-yyyy` placeholder text. No range picker for leave (two separate From/To fields), no calendar, no highlight of holidays or existing leave.
- **Checkboxes are the browser default** in Approvals; no select-all.
- **Button hierarchy is weak.** Primary is a filled orchid pill; everything else is the same translucent white pill. Specific problems:
  - `Review` buttons in Approvals read as plain text, nothing says they are clickable.
  - `Approve selected (0)` and `Save delegation` look like plain grey text; the disabled style (`opacity: 0.6`) and the secondary style are hard to tell apart.
  - `Change password` and `Sign out` are two equal chunky buttons in the top bar. Every competitor puts account actions behind an avatar menu.
  - `Save correction` and `Send week back to employee` sit side by side; the second is marked only by pink text.
  - No icon on any button, no spinner inside a button (only the label changes to `Signing in…`).
- **Segmented control and tabs** (`Grid | Day`, `Timesheets 6 | Leave 0`) work, but the count badge is a tiny filled pill that is the only accent on the tab.

Recommended replacements (keep React 19, no framework change): a shared `Select` built as a listbox/combobox with search and avatars; a date-range popover with a month grid; a `Button` with variants (primary, secondary, ghost, danger), sizes, leading icon and a built-in busy state; an avatar menu in the top bar (profile, change password, theme, sign out); styled checkboxes with select-all and a sticky bulk-action bar. Radix or Base UI primitives would do the accessibility work; the project only has React and Vite today, so adding one is a decision to make.

## 3. UI and visual style

Fact: the app is a "baby pink and lavender glass" theme: translucent panels with `backdrop-filter: blur(18px)` on the top bar, the sidebar and every card, over a pastel gradient, one orchid accent, Geist font.

Outdated or weak:
1. **Glassmorphism on everything.** Competitors use flat white surfaces with 1px borders and one strong accent (Zoho blue/red, Keka purple, BambooHR green, Factorial red). Blur on every card also costs rendering time on low-end laptops. Keep glass for one layer at most.
2. **Pastel pink reads as consumer, not payroll.** Payslips and approvals are trust-heavy screens.
3. **Low contrast (likely, not measured).** Muted text (`#7d6c8d`) on a pink-white wash, 12px field labels and 11px uppercase table headers. Check with a contrast tool.
4. **Everything is a card.** Page, section, stat strip and form all sit in the same rounded card, so nothing stands out.
5. **Wide forms.** On HR admin the Reason box and inputs stretch the full width of a 1440px screen. Cap near 640px.
6. ~~Week grid overflow~~ Retracted: the clipping in the first full-page Week screenshot was a screenshot artifact. A normal viewport capture shows the chip and cards fit.
7. **Technical text on screen.** Roles show as `employee, hr, manager`; the Week row reads `Training · Training`; the HR form asks for `Entry id to change`, a raw database id.

## 4. Tabs and navigation

- Fixed left sidebar with three all-caps group labels (`ME`, `MANAGER`, `HR`). Fine for five items; it has no collapse to a rail. Keka's published dashboard shows an icon rail (Engage, Hire, Perform, Project, Time, Payroll).
- No home/dashboard page: the first screen after sign-in is the Week grid. Competitors open on a personal home (BambooHR's `Hi, Maya` card, Zoho and Keka dashboards): who is out today, pending approvals, balance, next payslip.
- No search or command palette, no notifications bell, no breadcrumbs, no help entry.
- Every signed-in user sees every nav item (a code comment in `App.tsx` says role checks come later), so an employee sees `HR admin`.
- Page tabs (HR admin: `Time corrections | Leave setup | Payslip batch`) sit in their own glass pill; a flat underline row would free vertical space.

## 5. Arrangement of things

- Page headers are inconsistent: Week puts prev/next/This week beside the title and Grid/Day at the far right; Leave and HR have only a title. Define one header pattern (title, optional subtitle, primary action on the right).
- Leave shows a single balance as a full-width bar with `16 of 16 hours left (8 hours = 1 day)`. Use compact tiles in days.
- Approvals: the delegation form sits under the table at the same weight as the table. It is a rare action; put it behind a `Delegate` button and a side panel.
- The stat strip on Week (`1 h`, `39 h`, weekday bars) is the best-composed block in the app; reuse that style for the missing home page.

## 6. Data views and themes

- **Only one way to see data.** Week has Grid and Day. Leave has no calendar or team calendar. Approvals is a flat table; competitors show who is out and coverage conflicts.
- **Dark mode exists** and renders cleanly (HR admin dark is readable, accent holds). But it follows the OS only: the CSS supports `data-theme="light"` yet there is no toggle in the UI. Add Light / Dark / System in the avatar menu.
- **Empty states are thin.** My requests on Leave is a table header over blank space. Add a composed empty state with an action.
- **Tables** have no sorting, filtering, pagination or grouping; `Asha Rao` repeats three times in Approvals.
- Charts: one bar chart. A weekly/monthly utilisation view is the natural next one for a timesheet product.

## 7. Colour code

- One accent (orchid `#8f57c4`) plus soft green, amber and red for status. Disciplined, and it matches the "one accent" rule. Weak spot: amber is used for both `submitted` status and short-hours cells, so one colour means two things.
- Status chips are lower-case words in pills. Add an icon so colour is never the only signal.
- Dark mode shadows are pure black while light mode shadows are tinted pink, so the light source is not consistent across themes.

## 8. Animations

- Fact (from the CSS; I did not watch them play): staggered `rise` on every section, spring easing on buttons and bars, shimmer skeletons, a pulsing dot on warning chips. `prefers-reduced-motion` is respected. This is the strongest part of the UI.
- Gaps: the 0.7s entrance replays on every route change, which will feel slow for daily use (cut to about 250ms for repeat views); no motion when dropdowns open; no toast on save; no count-up on stats.
- Competitors use motion mainly on the landing page (Factorial's typing prompt box and logo marquee with a pause button, Keka's floating dashboard). Their product screens are calm.

## 9. Prioritised change list

P0, blocks the product looking finished
1. Real landing page at `/`, sign-in moved to `/login`.
2. Shared Button component with real variants, icons and busy state; fix `Review`, `Approve selected`, `Save delegation`.
3. Custom Select/Combobox with search; replace every native `<select>`.
4. Date-range picker for leave; replace native date inputs.
5. Avatar menu in the top bar; remove the two loose buttons.
6. ~~Fix the Week right-edge overflow~~ (retracted, see section 3).

P1, makes it feel modern
7. Home dashboard after sign-in (balance, pending approvals, who is out, next payslip).
8. Theme toggle (Light / Dark / System).
9. Flat surfaces instead of glass everywhere; re-check contrast.
10. Role-based nav.
11. Composed empty states; toast on save; busy state inside buttons.
12. Plain-language labels (no `Entry id`, no role string, no `Training · Training`).

P2, polish
13. Team leave calendar and list/calendar toggle.
14. Sortable, filterable tables grouped by person.
15. Icon-rail sidebar collapse, command palette (Ctrl+K), notifications bell.
16. Shorter route transitions; popover motion.
17. Typography: sentence-case table headers, 13px minimum for labels, form width cap.

## 10. Risks and caveats

- Marketing pages are curated: copy their patterns, not their polish. 4.6/5 and "17,000 companies" are vendor claims, unverified.
- A landing page needs real content: a product screenshot, claims you can support, and legal pages. Placeholder copy hurts more than no landing page.
- Custom select and date pickers are accessibility-sensitive; use a vetted primitive.
- The theme change is cheap (one 200-line file, `web/src/app.css`). The component work (items 2 to 5) is where the effort is.

## Sources

- Zoho People: https://www.zoho.com/people/ (captured 2026-11-18)
- Keka: https://www.keka.com/
- Factorial: https://factorialhr.com/
- BambooHR: https://www.bamboohr.com/
- Rippling: https://www.rippling.com/ (redirected to the India "global" product page)
- Our app: `web/src/app.css`, `web/src/App.tsx`, `web/src/ui.tsx`, running on localhost
