# WorkHub database ERD

Source: `documentation/docs/superpowers/specs/2026-11-12-workhub-design.md` section 5. Renders on GitHub.

Note: the user table is named `app_user` in the database because `user` is reserved in Postgres.

Conventions (apply to every table): `id` primary key, `created_at` and `updated_at` timestamps. Time is stored as **integer minutes**, dates as `date`. PK = primary key, FK = foreign key, UK = unique.

## Migration plan

| Migration | Tables | When |
|---|---|---|
| 1. Core (WH-03) | Diagrams 1 and 2: organisation, people, projects, tasks, time, approvals, audit, job | 16–20 Nov |
| 2. Leave (WH-40/41) | Diagram 3, leave tables | 2–11 Dec |
| 3. Payslips (WH-50) | Diagram 3, payslip tables | 14–16 Dec |
| 4. Notifications (WH-60) | Diagram 3, notification tables | 21–23 Dec |
| Done: approval due days (WH-32) | Column `org_settings.approval_due_working_days` | migration 0002, 16 Nov |
| Done: edit requests (WH-22) | Table `edit_request` | migration 0003, 16 Nov |
| Done: per-day approval | Table `day_decision` | migration 0004, 16 Nov |
| Done: leave (WH-40/41) | Tables `leave_type`, `leave_balance`, `leave_request`, `blackout_day` | migration 0005, 17 Nov |
| Stretch / later | `running_timer`, `suggestion`, `anomaly`, `saved_view`, `project_template`, `status_report`, `integration_account`, `repo_link`, client portal tables | after Dec 24 |

## Rules the database must enforce

- `time_entry` points to **exactly one** of `task_id` or `charge_code_id` (CHECK constraint).
- `minutes` is between 1 and 1440 per entry; the 24 h per day total is checked in the API.
- No future dates: checked in the API, not the database.
- `timesheet_week` is unique per (`user_id`, `week_start`).
- `approval.subject_type` + `subject_id` is a polymorphic reference (week, leave, comp_off, edit_request), so there is no real foreign key. The API checks it.
- `audit_event` is append-only: no update or delete grants for the app user.
- A manager can decide a whole week or one day at a time. An approved day is locked (`day_decision`); when every day with time is approved the week is approved and locked, otherwise it returns to draft and only the sent-back days go to the manager again on resubmit. A week can be edited until it is approved.
- Manager chain must not loop (`user.manager_id` is checked in the API on save).
- Approved leave writes `time_entry` rows with `source = 'leave'` in the same transaction as the balance deduction.

## 1. Organisation, people and work

```mermaid
erDiagram
  ORG_SETTINGS {
    int id PK
    string work_week_days "default Mon-Fri"
    string week_start "Monday or Sunday"
    int daily_expected_minutes "default 480"
    int fy_start_month "default 4"
    bool client_portal_enabled "default false"
    int approval_due_working_days "default 2"
  }
  LOCATION ||--o{ HOLIDAY : has
  LOCATION ||--o{ APP_USER : works_at
  LOCATION {
    int id PK
    string name
  }
  HOLIDAY {
    int id PK
    int location_id FK
    date on_date
    string name
  }
  APP_USER ||--o{ ROLE_ASSIGNMENT : holds
  APP_USER ||--o{ APP_USER : manages
  APP_USER ||--o{ TEAM_MEMBER : joins
  TEAM ||--o{ TEAM_MEMBER : has
  APP_USER {
    int id PK
    string employee_code UK
    string name
    string email UK
    string designation
    string department
    int location_id FK
    int manager_id FK "self reference"
    date joined_on
    date exited_on
    bool active
  }
  ROLE_ASSIGNMENT {
    int id PK
    int user_id FK
    string role "employee manager hr finance admin"
  }
  TEAM {
    int id PK
    string name
  }
  TEAM_MEMBER {
    int team_id FK
    int user_id FK
  }
  CLIENT ||--o{ WORK_ORDER : has
  WORK_ORDER ||--o{ PROJECT : funds
  CLIENT {
    int id PK
    string name
  }
  WORK_ORDER {
    int id PK
    int client_id FK
    string code UK "for example SOW-11101"
    date starts_on
    date ends_on
  }
  PROJECT ||--o{ PROJECT_MEMBER : has
  PROJECT ||--o{ PROJECT_TEAM : has
  PROJECT ||--o{ TASK_LIST : has
  PROJECT ||--o{ TASK_STATUS : defines
  APP_USER ||--o{ PROJECT_MEMBER : joins
  TEAM ||--o{ PROJECT_TEAM : joins
  PROJECT {
    int id PK
    string key UK "for example ATPL-106"
    string name
    string group_name
    string status
    string visibility "public or private"
    int manager_id FK
    int work_order_id FK
  }
  PROJECT_MEMBER {
    int project_id FK
    int user_id FK
    string project_role
  }
  PROJECT_TEAM {
    int project_id FK
    int team_id FK
  }
  TASK_LIST ||--o{ TASK : groups
  TASK_STATUS ||--o{ TASK : state_of
  TASK ||--o{ TASK : subtask_of
  TASK ||--o{ TASK_OWNER : assigned_to
  TASK_LIST {
    int id PK
    int project_id FK
    string name
    int position
  }
  TASK_STATUS {
    int id PK
    int project_id FK
    string name
    int position
    bool is_closed
  }
  TASK {
    int id PK
    int task_list_id FK
    int status_id FK
    string key UK "for example AS1-T4"
    string title
    text description
    string priority
    date start_on
    date due_on
    int parent_id FK "self reference"
    bool is_milestone
  }
  TASK_OWNER {
    int id PK
    int task_id FK
    int user_id FK "user or team, one is set"
    int team_id FK
  }
  CHARGE_CODE ||--o{ CHARGE_CODE_TEAM : shared_with
  TEAM ||--o{ CHARGE_CODE_TEAM : may_use
  CHARGE_CODE {
    int id PK
    string code UK "Bench Training Proposal"
    string name
    bool active
  }
  CHARGE_CODE_TEAM {
    int charge_code_id FK
    int team_id FK
  }
```

## 2. Time, approvals, audit and jobs

```mermaid
erDiagram
  APP_USER ||--o{ TIMESHEET_WEEK : owns
  TIMESHEET_WEEK ||--o{ TIME_ENTRY : contains
  TASK ||--o{ TIME_ENTRY : logged_on
  CHARGE_CODE ||--o{ TIME_ENTRY : logged_on
  TIMESHEET_WEEK {
    int id PK
    int user_id FK
    date week_start "unique with user_id"
    string status "draft submitted approved sent_back"
    datetime locked_at
  }
  TIME_ENTRY {
    int id PK
    int user_id FK
    int week_id FK
    date work_date
    int minutes "integer minutes"
    int task_id FK "exactly one of task or charge code"
    int charge_code_id FK
    bool billable
    text notes
    string source "manual timer calendar git leave holiday"
    text sent_back_reason
  }
  APP_USER ||--o{ APPROVAL : requests
  APP_USER ||--o{ APPROVAL : approves
  APPROVAL ||--o{ APPROVAL_STEP : records
  APP_USER ||--o{ APPROVAL_STEP : acts
  APPROVAL {
    int id PK
    string subject_type "week leave comp_off edit_request"
    int subject_id "polymorphic, no foreign key"
    int requester_id FK
    int approver_id FK
    int level
    string status "pending approved sent_back cancelled"
    datetime due_at "escalation time"
    text reason
  }
  APPROVAL_STEP {
    int id PK
    int approval_id FK
    int actor_id FK
    string action
    text comment
    datetime at
  }
  APP_USER ||--o{ DELEGATION : hands_over
  APP_USER ||--o{ DELEGATION : receives
  DELEGATION {
    int id PK
    int from_user_id FK
    int to_user_id FK
    date starts_on
    date ends_on
  }
  APP_USER ||--o{ AUDIT_EVENT : acts
  AUDIT_EVENT {
    int id PK
    int actor_id FK
    string entity
    int entity_id
    string action
    json before
    json after
    datetime at "append only"
  }
  TIMESHEET_WEEK ||--o{ DAY_DECISION : decided_by_day
  APP_USER ||--o{ DAY_DECISION : decides
  DAY_DECISION {
    int id PK
    int week_id FK "unique with work_date"
    date work_date
    string status "approved or sent_back; no row means still waiting"
    text reason
    int decided_by FK
  }
  TIMESHEET_WEEK ||--o{ EDIT_REQUEST : changes
  APP_USER ||--o{ EDIT_REQUEST : files
  EDIT_REQUEST {
    int id PK
    int week_id FK
    int requester_id FK
    text reason
    json changes "list of add, update or delete of entries"
    string status "pending approved rejected cancelled"
  }
  JOB {
    int id PK
    string kind
    json payload
    datetime run_at
    int attempts
    text last_error
    string status
  }
```

## 3. Later migrations: leave, payslips, notifications

```mermaid
erDiagram
  APP_USER ||--o{ LEAVE_BALANCE : has
  LEAVE_TYPE ||--o{ LEAVE_BALANCE : of_type
  APP_USER ||--o{ LEAVE_REQUEST : applies
  LEAVE_TYPE ||--o{ LEAVE_REQUEST : of_type
  APP_USER ||--o{ COMP_OFF_REQUEST : earns
  LEAVE_TYPE {
    int id PK
    string name UK
    bool paid
    int charge_code_id FK "leave time entries are booked to it"
    int accrual_per_month "stored as minutes, the API shows hours"
    int carry_forward_cap "stored as minutes, the API shows hours"
    int attachment_after_days
  }
  LEAVE_BALANCE {
    int id PK
    int user_id FK
    int leave_type_id FK
    int leave_year
    int opening
    int accrued
    int used
    int adjusted
  }
  LEAVE_REQUEST {
    int id PK
    int user_id FK
    int leave_type_id FK
    date from_date
    date to_date
    json day_portions "date to full, first_half or second_half"
    int minutes "total, counted from the portions"
    text reason
    string attachment_key
    string status "applied approved rejected withdrawn cancelled"
    bool applied_after_dates
  }
  COMP_OFF_REQUEST {
    int id PK
    int user_id FK
    date worked_on
    int minutes
    text reason
    string status
  }
  BLACKOUT_DAY {
    int id PK
    date on_date UK "organisation-wide; team scope comes later"
    text note
  }
  PAYSLIP_BATCH ||--o{ PAYSLIP : contains
  APP_USER ||--o{ PAYSLIP : receives
  APP_USER ||--o{ DOCUMENT : owns
  PAYSLIP_BATCH {
    int id PK
    string month
    int uploaded_by FK
    string status "draft or published"
    json match_report
  }
  PAYSLIP {
    int id PK
    int batch_id FK
    int user_id FK
    string file_key "object storage key"
  }
  DOCUMENT {
    int id PK
    int user_id FK
    string type "form16 or letter"
    string file_key
    int year
  }
  APP_USER ||--o{ NOTIFICATION : gets
  APP_USER ||--o{ NOTIFICATION_PREF : sets
  NOTIFICATION {
    int id PK
    int user_id FK
    string event
    json payload
    string group_key
    datetime read_at
  }
  NOTIFICATION_PREF {
    int id PK
    int user_id FK
    string event
    string channels "in_app email teams digest"
  }
```
