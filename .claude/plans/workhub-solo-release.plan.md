# Plan: Milestone 1, sign in and log a week

**Source PRD**: .claude/prds/workhub-solo-release.prd.md
**Selected Milestone**: 1, Sign in and log a week (due Fri Nov 20)
**Complexity**: Medium (backend small, frontend is the risk)

## Summary
Replace the dev-only `X-User-Id` header with real email and password sign-in using opaque session tokens. Then stand up `web/` on Bun with a generated API client, a login screen and a minimal week grid. Time available: about 15 hours, Wed to Fri.

## Patterns to Mirror
| Category | Source | Pattern |
|---|---|---|
| Models | `api/src/workhub_api/models.py:85` (`User`), `:318` (`DayDecision`) | `Stamped, Base` classes, `_fk(...)` helper, unique and check constraints through `__table_args__` |
| Migration | `api/migrations/versions/0004_day_decision.py` | `op.create_table` with `op.f(...)` constraint names, `id`, `created_at` and `updated_at` columns, a real `downgrade` |
| Auth dependency | `api/src/workhub_api/db.py:20` (`current_user`) | Every endpoint depends on `CurrentUser`, so changing that one function covers them all |
| Router | `api/src/workhub_api/leave.py`, `delegations.py` | One module with `router`, included in `main.py` |
| Roles | `api/src/workhub_api/permissions.py` | `require_roles(...)` dependencies, 401 for no sign-in and 403 for no role |
| Tests | `api/tests/conftest.py:38` (`world` fixture) | Real Postgres in a rolled-back transaction, `TestClient`, `hdr(user)` helper |
| Seed | `api/src/workhub_api/seed.py:46` | Idempotent `seed(session)` that returns False if already there |

## Design decisions (to confirm)
- **Passwords:** hash with the standard library's `hashlib.scrypt` (no new dependency). Store the salt and hash in one string column.
- **Sessions:** the login returns a random token, and only its SHA-256 hash is stored. The client sends `Authorization: Bearer <token>`. Sessions expire after 7 days, and logout deletes the row.
- **Keep the dev header:** `current_user` checks the Bearer token first. The `X-User-Id` header is honoured only when `DEV_AUTH` is on, so the 20 existing test files keep working unchanged.
- **Accounts:** HR sets initial passwords. Password reset by email is out of scope for now.
- **Throttling:** a per-email limit on failed attempts, kept simple and stored in the database.

## Files to Change
| File | Action | Why |
|---|---|---|
| `api/src/workhub_api/models.py` | UPDATE | Add `Credential` (one per user) and `AuthSession` |
| `api/migrations/versions/0006_auth.py` | CREATE | The two tables, with a downgrade |
| `api/src/workhub_api/auth.py` | CREATE | Hash and verify password, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, and `POST /auth/password` (change own) |
| `api/src/workhub_api/db.py` | UPDATE | `current_user` reads the Bearer token, with the dev header as fallback |
| `api/src/workhub_api/main.py` | UPDATE | Include the auth router and add CORS for the web app's origin |
| `api/src/workhub_api/seed.py` | UPDATE | Give the 3 seeded users a known dev password (and add a few leave types) |
| `api/tests/test_auth_login.py` | CREATE | Login, bad password, expired session, logout, header fallback |
| `api/README.md` | UPDATE | Sign-in section, replacing the "not wired in" notes |
| `web/` (new) | CREATE | Bun and Vite React app, with `bun run gen:api` to build the typed client from `/openapi.json` |
| `web/src/` login page, protected route, week page | CREATE | Login, then a minimal week grid |

## Tasks
### Task 1: Sign-in tests first (Wed, about 1.5h)
- **Action**: Write failing tests in `test_auth_login.py` for: good login returns a token, wrong password gives 401, unknown email gives 401 with the same message, expired token gives 401, logout kills the token, `/auth/me` returns the user and roles, a deactivated user cannot sign in.
- **Mirror**: `conftest.py` `world` fixture.
- **Validate**: `uv run pytest tests/test_auth_login.py` (fails for the right reason).

### Task 2: Migration 0006 (Wed, about 1h)
- **Action**: Add `credential` (`user_id` unique, `password_hash`, `must_change`) and `auth_session` (`user_id`, `token_hash` unique, `expires_at`, `last_used_at`). Use the alembic skill and database-reviewer.
- **Mirror**: `0004_day_decision.py`.
- **Validate**: `uv run alembic upgrade head`, then `downgrade -1`, then `upgrade head` on a local Docker database first.

### Task 3: Implement auth (Wed, about 2h)
- **Action**: Build `auth.py` and update `current_user`. Keep the 401 and 403 behaviour. Compare the hash in constant time. Update `seed.py` with dev passwords.
- **Mirror**: `permissions.py`, `leave.py` router.
- **Validate**: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`.

### Task 4: Apply to workhub_1 and set passwords (Wed end, about 0.5h)
- **Action**: `uv run alembic upgrade head`, then add credentials for the existing seeded users (the seed skips when users exist, so add a small set-password command or script).
- **Validate**: `alembic current` shows `0006 (head)`, and a login against the local server returns a token.

### Task 5: Scaffold web/ (Thu, about 2h)
- **Action**: `bun create vite web --template react-ts`, add a generated typed client from `http://localhost:8000/openapi.json`, an env setting for the API URL, and token storage with a 401 redirect to login.
- **Validate**: `bun run build` passes and the login page loads.

### Task 6: Login and shell (Thu, about 3h)
- **Action**: Login form, a protected route, a header with the user's name and logout, and an error message for wrong credentials.
- **Validate**: sign in as a seeded user in the browser, refresh and stay signed in, log out.

### Task 7: Week grid (Fri, about 4h)
- **Action**: Show `GET /time/week`, add and edit entries (task or charge code, minutes, date), show day totals and the status, and a Submit button. Show send-back reasons if present.
- **Validate**: log a week and submit it, then check the approval appears in the manager's `GET /approvals/inbox`.

### Task 8: Demo and fixes (Fri, about 1h)
- **Action**: Run the full journey, fix what breaks, and update `api/README.md` and the PRD milestone status.

## Validation
```bash
cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd web && bun run build
```

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| Week grid takes more than 4h | High | Fallback: demo sign-in in the UI and log the week through `/docs`, finish the grid Monday |
| Existing tests break when `current_user` changes | Low | Keep the `X-User-Id` path under `DEV_AUTH`; run the whole suite after Task 3 |
| Browser blocked by CORS | Medium | Add CORS for the web origin in Task 3, not at the end |
| Azure latency makes UI feel slow | Medium | Develop against local Docker Postgres, check against `workhub_1` for the demo |
| Passwords for real staff | Medium | Not needed for the demo; seed passwords are dev only and `must_change` is set for real accounts later |

## Acceptance
- [ ] A seeded user signs in with email and password and gets a session
- [ ] Wrong password, expired session and a deactivated user all give 401
- [ ] The dev header only works with `DEV_AUTH` on, and the full test suite passes
- [ ] Migration 0006 upgrades and downgrades cleanly, and is applied to `workhub_1`
- [ ] In the browser: sign in, log a week, submit it, and the manager sees it in the inbox
- [ ] `api/README.md` describes sign-in v1
