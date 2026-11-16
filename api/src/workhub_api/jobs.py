"""Job queue on Postgres (WH-07): enqueue work now or later, and a worker runs it.

A job is a row in `job`. The worker claims the next due row with FOR UPDATE SKIP LOCKED, so
several workers never run the same job. The handler runs inside a savepoint: if it fails, its
database changes are undone, the attempt is counted, and the job is retried later with a growing
delay, until MAX_ATTEMPTS, then it is marked failed. If the worker dies mid-job, the transaction
ends, the lock goes, and the job is simply picked up again. So handlers may run more than once
and should be safe to repeat.

Register a handler:   @handler("send_digest")
                      def send_digest(session: Session, payload: dict[str, Any]) -> None: ...
Queue work:           enqueue(session, "send_digest", {"user_id": 7}, run_at=...)   # caller commits
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from workhub_api.models import Job

log = logging.getLogger("workhub.jobs")

Handler = Callable[[Session, dict[str, Any]], None]
HANDLERS: dict[str, Handler] = {}
MAX_ATTEMPTS = 5
BACKOFF_SECONDS = 30  # doubles after each failed attempt: 30 s, 60 s, 120 s, 240 s


def handler(kind: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        HANDLERS[kind] = fn
        return fn

    return register


def enqueue(
    session: Session,
    kind: str,
    payload: dict[str, Any] | None = None,
    run_at: datetime | None = None,
) -> Job:
    """Add a job. It joins the caller's transaction, so it exists only if the caller commits."""
    job = Job(kind=kind, payload=payload, run_at=run_at or datetime.now(UTC))
    session.add(job)
    return job


def ensure_queued(session: Session, kind: str) -> bool:
    """For repeating jobs: queue `kind` unless one is already waiting. True if it added one."""
    if session.scalar(select(Job.id).where(Job.kind == kind, Job.status == "queued").limit(1)):
        return False
    enqueue(session, kind)
    return True


def run_one(session: Session, kinds: set[str] | None = None) -> bool:
    """Run the next due job (only of `kinds`, if given). False when nothing is due."""
    now = datetime.now(UTC)
    query = select(Job).where(Job.status == "queued", Job.run_at <= now)
    if kinds is not None:
        query = query.where(Job.kind.in_(kinds))
    job = session.scalars(
        query.order_by(Job.run_at, Job.id).limit(1).with_for_update(skip_locked=True)
    ).first()
    if job is None:
        return False
    job.attempts += 1
    try:
        run = HANDLERS[job.kind]
        with session.begin_nested():  # undo the handler's changes if it fails
            run(session, job.payload or {})
    except Exception as exc:  # a job must never take the worker down
        job.last_error = f"{type(exc).__name__}: {exc}"[:2000]
        if job.attempts >= MAX_ATTEMPTS:
            job.status = "failed"
        else:
            delay = BACKOFF_SECONDS * 2 ** (job.attempts - 1)
            job.run_at = datetime.now(UTC) + timedelta(seconds=delay)
        log.warning("job %s (%s) failed, attempt %s: %s", job.id, job.kind, job.attempts, exc)
    else:
        job.status = "done"
        job.last_error = None
    session.commit()
    return True
