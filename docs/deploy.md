# WorkHub: deploy, backup and rollback (Azure)

Written for the release candidate (target Dec 24). It is a runbook, not yet rehearsed: the dry run in
the checklist at the end is where it gets tried for real.

## Shape

| Piece | Where | Notes |
|---|---|---|
| Database | Azure Database for PostgreSQL | A **separate production database**, not `workhub_1`. The dev database holds seed users with a shared dev password and test payslips. |
| API | Azure Container Apps, image from `api/Dockerfile` | Same region as the database (each call is about 250 ms from a laptop, a few ms in-region). |
| Worker | Second Container App, same image, command `python -m workhub_api.worker` | Exactly **one** replica. It runs approval housekeeping and monthly leave accrual. |
| Migrations | A one-off job, same image, command `alembic upgrade head` | Run before the new API revision takes traffic. |
| Web | Azure Static Web Apps (or any static host) | `cd web && VITE_API_URL=https://<api> bun run build`, publish `web/dist`. |

Payslip PDFs are stored in Postgres, so the database backup covers them. There is no separate file store.

## API settings (Container App environment, secrets from Key Vault or the app's secret store)

```
POSTGRES_HOST=<server>.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB   # the production database
POSTGRES_SSLMODE=verify-full                      # plus POSTGRES_SSLROOTCERT, see api/README.md
DEV_AUTH=false                                    # must be false; the X-User-Id header is a backdoor when true
WEB_ORIGIN=https://<web host>                     # the one origin allowed by CORS
```

The web build bakes in `VITE_API_URL`, so it is set at build time, not at run time.

## First deploy

1. Create the production database and an admin user for it. Allow the Container Apps' outbound IPs through the Postgres firewall (or use a private endpoint).
2. Run the migration job (`alembic upgrade head`) against it.
3. Create the first HR/admin account by hand. **Never run `python -m workhub_api.seed` in production.** It gives every user the shared dev password. After that, HR adds people from the admin screens (`/admin/users`).
4. Deploy the API, then the worker, then publish the web build.
5. Check `GET /health` returns `{"status":"ok"}` and sign in.

## Every later release

1. **Backup.** Take an on-demand backup of the production database (or note the point-in-time restore moment) and write down the time. Azure's automatic backups are not enough on their own for a migration day.
2. Check the migration locally on a throwaway database: `alembic upgrade head`, then `alembic downgrade -1`, then `alembic upgrade head` again.
3. Run the migration job.
4. Deploy the new API revision, then the worker, then the web build. Keep the previous API revision available.
5. Smoke test: `/health`, sign in, open a week, open Approvals, open Payslips.

## Rollback

- **Code only (no migration, or the migration is backward compatible):** switch traffic back to the previous API revision and re-publish the previous web build.
- **A migration went wrong:** stop the worker, run `alembic downgrade -1` with the previous image (each migration has a downgrade), then switch traffic back. If a downgrade is not enough or data is damaged, restore the backup from step 1 into a **new** database, point the API at it, and keep the damaged one for inspection. Anything entered after the backup time is lost, so say so to HR.
- Payslip publishing and leave approvals write audit events; check the audit log before deciding what to re-enter.

## Before the first real use (checklist)

- [ ] `DEV_AUTH=false` on every environment that is not a laptop
- [ ] Production database is separate from `workhub_1`; no seed users in it
- [ ] `POSTGRES_SSLMODE=verify-full` with Azure's root certificate
- [ ] Both CI workflows (`api-ci`, `web-ci`) are green on the release commit
- [ ] Migration tried on a throwaway database, up, down and up again
- [ ] A restore from backup has been tried once, into a scratch database
- [ ] One worker replica only
- [ ] Security sweep: permissions and audit on `/users`, `/payslips`, edit requests, HR actions
- [ ] Dry run with a month of real time, leave and payslips (target Dec 21)

## Not done yet

Sign-in has no rate limit beyond the 5-failure account lock. There is no alerting on the worker (if it stops,
approvals stop escalating and leave stops accruing without any message). Both are worth adding after the dry run.
