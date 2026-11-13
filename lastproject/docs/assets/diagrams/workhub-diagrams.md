# WorkHub diagram sources (Mermaid)

These are the content sources. The finished diagrams are redrawn in the Ampera skin (see the .html and .png files); Mermaid layout and styling are not used.

## 0 Context
```mermaid
flowchart LR
  staff[Employees and managers]
  ops[HR, Finance and Admin]
  cli[Client users - optional add-on]
  wh((WorkHub))
  m365[Microsoft 365]
  git[GitHub and GitLab]
  llm[LLM service]
  zoho[Zoho - one-off import]
  staff -->|log and approve| wh
  ops -->|manage and upload| wh
  cli -.->|reports| wh
  wh -->|sign-in, calendar, Teams| m365
  git -->|commits| wh
  wh -->|drafts| llm
  zoho -.->|import| wh
```

## 1 Containers
```mermaid
flowchart LR
  subgraph WorkHub
    api[API]
    wrk[Worker]
  end
  web[Web app]
  pg[(Postgres)]
  files[(File storage)]
  m365[Microsoft 365]
  git[GitHub and GitLab]
  llm[LLM service]
  web -->|HTTPS JSON| api
  api -->|SQL| pg
  api -->|signed URLs| files
  api -->|OIDC| m365
  wrk -->|jobs| pg
  wrk -->|batches| files
  wrk -->|calendar, Teams| m365
  wrk -->|commits| git
  wrk -->|drafts| llm
```

## 2 Deployment
```mermaid
flowchart LR
  subgraph Internet
    br[Browser]
  end
  subgraph AppZone
    px[Edge proxy]
    api[API x2]
    wk[Worker]
  end
  subgraph DataZone
    pg[(Postgres)]
    bl[(Object storage)]
  end
  ext[Microsoft 365, Git, LLM]
  br -->|HTTPS 443| px
  px -->|HTTP 8000| api
  api -->|TLS 5432| pg
  wk -->|TLS 5432| pg
  wk -->|HTTPS 443| bl
  wk -->|HTTPS 443| ext
```

## 3 ER organisation and work
```mermaid
erDiagram
  CLIENT ||--o{ WORK_ORDER : has
  WORK_ORDER ||--o{ PROJECT : funds
  PROJECT }o--o{ USER : members
  LOCATION ||--o{ USER : works_at
  USER }o--o{ TEAM : member_of
  TEAM }o--o{ CHARGE_CODE : may_use
  CLIENT { int id PK }
  WORK_ORDER { int id PK }
  PROJECT { int id PK }
  LOCATION { int id PK }
  USER { int id PK }
  TEAM { int id PK }
  CHARGE_CODE { int id PK }
```

## 4 ER time and approvals
```mermaid
erDiagram
  USER ||--o{ TIMESHEET_WEEK : owns
  TIMESHEET_WEEK ||--o{ TIME_ENTRY : has
  TIME_ENTRY }o--|| TASK : logs_on
  SUGGESTION |o--|| TIME_ENTRY : becomes
  TIMESHEET_WEEK ||--o{ APPROVAL : needs
  APPROVAL ||--o{ APPROVAL_STEP : logs
  DELEGATION }o--|| USER : hands_over
  USER { int id PK }
  TIMESHEET_WEEK { int id PK }
  TIME_ENTRY { int id PK }
  TASK { int id PK }
  SUGGESTION { int id PK }
  APPROVAL { int id PK }
  APPROVAL_STEP { int id PK }
  DELEGATION { int id PK }
```

## 5 ER leave and payslips
```mermaid
erDiagram
  USER ||--o{ LEAVE_BALANCE : has
  LEAVE_TYPE ||--o{ LEAVE_BALANCE : of_type
  USER ||--o{ LEAVE_REQUEST : applies
  USER ||--o{ COMP_OFF_REQUEST : earns
  USER ||--o{ PAYSLIP : receives
  PAYSLIP_BATCH ||--o{ PAYSLIP : contains
  DOCUMENT }o--|| USER : for
  USER { int id PK }
  LEAVE_TYPE { int id PK }
  LEAVE_BALANCE { int id PK }
  LEAVE_REQUEST { int id PK }
  COMP_OFF_REQUEST { int id PK }
  PAYSLIP_BATCH { int id PK }
  PAYSLIP { int id PK }
  DOCUMENT { int id PK }
```

## 6 Week lifecycle
```mermaid
stateDiagram-v2
  [*] --> Draft
  Draft --> Submitted : submit
  Submitted --> Submitted : escalate
  Submitted --> Approved : approve
  Submitted --> SentBack : send back
  SentBack --> Draft : employee edits
  Approved --> EditRequested : request edit
  EditRequested --> Approved : reject
  EditRequested --> Draft : allow edit
```

## 7 Sequence submit and approve
```mermaid
sequenceDiagram
  participant E as Employee
  participant W as Web app
  participant A as API
  participant K as Worker
  participant M as Manager
  E->>W: submit week
  W->>A: POST submit
  A->>A: check rules
  A-->>W: submitted
  A-)K: queue notice
  K-)M: notify
  M->>W: approve
  W->>A: POST approve
  A->>A: lock and audit
  A-->>W: approved
  A-)K: notify
  K-)E: approved
```

## 8 Sequence leave approval
```mermaid
sequenceDiagram
  participant E as Employee
  participant L as Leave module
  participant P as Approval engine
  participant T as Time module
  participant M as Manager
  E->>L: apply leave
  L->>L: check rules
  L->>P: create
  P-)M: notify
  M->>P: approve
  P->>L: approved
  L->>L: deduct days
  L->>T: fill week
  T-->>L: done
  L-)E: approved
```

## 9 Suggestion pipeline
```mermaid
flowchart LR
  cal[Outlook calendar]
  git[GitHub and GitLab]
  sync[Sync job]
  match[Matching rules]
  llm[LLM service]
  store[(Suggestions)]
  ui[Week view]
  entry[(Time entries)]
  cal -->|events| sync
  git -->|commits| sync
  sync -->|candidates| match
  match -.->|tidy notes| llm
  match -->|proposals| store
  store -->|side panel| ui
  ui -->|accept| entry
```

## 10 Sitemap
```mermaid
flowchart TD
  root[WorkHub]
  my["My space: Week, Leave, Payslips, Notifications"]
  mgr["Manage: Approvals, Team calendar, Dashboard"]
  work["Work: Clients, Projects, Tasks"]
  adm["Admin: Users, Holidays, Leave types, Payslips, Audit"]
  ins["Insights: Reports, Status reports"]
  root --> my
  root --> mgr
  root --> work
  root --> adm
  root --> ins
```

## 11 Access flow
```mermaid
flowchart TD
  start([Open WorkHub]) --> sso[Sign in with Microsoft]
  sso --> d1{Email matches an active user?}
  d1 -- yes --> roles[Load roles and reporting line]
  d1 -- no --> deny[Access denied]
  roles --> d2{Allowed to see this record?}
  d2 -- yes --> show[Show the record]
  d2 -- no --> hide[Return not found]
```
