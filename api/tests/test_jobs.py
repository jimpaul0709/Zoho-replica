from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from workhub_api import jobs
from workhub_api.db import engine
from workhub_api.models import Job, Location

KINDS = {"t-ok", "t-boom", "t-writes", "t-nope", "t-first", "t-second"}  # only our own jobs


@pytest.fixture
def session() -> Iterator[Session]:
    """Rolled back at the end, so the shared database stays clean."""
    conn = engine.connect()
    outer = conn.begin()
    s = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield s
    finally:
        s.close()
        outer.rollback()
        conn.close()


def run(s: Session) -> bool:
    return jobs.run_one(s, kinds=KINDS)


def test_runs_a_due_job_once(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, Any]] = []
    monkeypatch.setitem(jobs.HANDLERS, "t-ok", lambda s, payload: seen.append(payload))
    job = jobs.enqueue(session, "t-ok", {"user_id": 7})
    session.flush()
    assert run(session) is True
    assert seen == [{"user_id": 7}]
    assert (job.status, job.attempts, job.last_error) == ("done", 1, None)
    assert run(session) is False  # nothing left to do


def test_jobs_for_later_wait_and_earlier_ones_go_first(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order: list[str] = []
    monkeypatch.setitem(jobs.HANDLERS, "t-first", lambda s, p: order.append("first"))
    monkeypatch.setitem(jobs.HANDLERS, "t-second", lambda s, p: order.append("second"))
    now = datetime.now(UTC)
    later = jobs.enqueue(session, "t-ok", run_at=now + timedelta(hours=1))
    jobs.enqueue(session, "t-second", run_at=now - timedelta(minutes=1))
    jobs.enqueue(session, "t-first", run_at=now - timedelta(minutes=5))
    session.flush()
    while run(session):
        pass
    assert order == ["first", "second"]
    assert later.status == "queued"  # not due yet


def test_failure_undoes_the_handler_and_retries_later(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def writes_then_fails(s: Session, payload: dict[str, Any]) -> None:
        s.add(Location(name="should-not-survive"))
        s.flush()
        raise RuntimeError("boom")

    monkeypatch.setitem(jobs.HANDLERS, "t-writes", writes_then_fails)
    job = jobs.enqueue(session, "t-writes")
    session.flush()
    assert run(session) is True
    assert (job.status, job.attempts) == ("queued", 1)
    assert job.last_error == "RuntimeError: boom"
    assert job.run_at > datetime.now(UTC) + timedelta(seconds=20)  # backed off about 30 s
    assert (
        session.scalars(select(Location).where(Location.name == "should-not-survive")).first()
        is None
    )
    assert run(session) is False  # not due again yet


def test_gives_up_after_max_attempts(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(s: Session, payload: dict[str, Any]) -> None:
        raise RuntimeError("boom")

    monkeypatch.setitem(jobs.HANDLERS, "t-boom", boom)
    job = jobs.enqueue(session, "t-boom")
    session.flush()
    for _ in range(jobs.MAX_ATTEMPTS):
        job.run_at = datetime.now(UTC) - timedelta(seconds=1)  # skip the waiting
        session.flush()
        assert run(session) is True
    assert (job.status, job.attempts) == ("failed", jobs.MAX_ATTEMPTS)
    assert run(session) is False  # a failed job is not picked again


def test_unknown_kind_fails_instead_of_crashing(session: Session) -> None:
    job = jobs.enqueue(session, "t-nope")
    session.flush()
    assert run(session) is True
    assert job.attempts == 1 and job.last_error is not None and "t-nope" in job.last_error


def test_ensure_queued_adds_one_waiting_job_only(session: Session) -> None:
    assert jobs.ensure_queued(session, "t-ok") is True
    session.flush()
    assert jobs.ensure_queued(session, "t-ok") is False
    assert len(session.scalars(select(Job).where(Job.kind == "t-ok")).all()) == 1
