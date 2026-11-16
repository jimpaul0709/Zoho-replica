"""Shared test setup: the app wired to one session inside a transaction that is rolled back."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from workhub_api.config import settings
from workhub_api.db import engine, get_session
from workhub_api.main import app
from workhub_api.models import (
    ChargeCode,
    Project,
    Task,
    TaskList,
    TaskStatus,
    User,
)

DAY = date.today() - timedelta(days=7)


@dataclass
class World:
    session: Session
    client: TestClient
    emp: User
    boss: User
    task: Task
    code: ChargeCode


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> Iterator[World]:
    """An employee with a manager, one task and one charge code. Nothing is kept afterwards."""
    monkeypatch.setattr(settings, "dev_auth", True)
    conn = engine.connect()
    outer = conn.begin()
    s = Session(bind=conn, join_transaction_mode="create_savepoint")
    app.dependency_overrides[get_session] = lambda: s

    boss = User(employee_code="B1", name="Boss", email="boss@x.io")
    s.add(boss)
    s.flush()
    emp = User(employee_code="E1", name="Emp", email="emp@x.io", manager_id=boss.id)
    project = Project(key="P-1", name="P")
    s.add_all([emp, project])
    s.flush()
    task_list = TaskList(project_id=project.id, name="L")
    status = TaskStatus(project_id=project.id, name="Open")
    s.add_all([task_list, status])
    s.flush()
    task = Task(task_list_id=task_list.id, status_id=status.id, key="P-1-T1", title="T")
    code = ChargeCode(code="T-Bench", name="T-Bench")  # not "Bench": the real seed has that one
    s.add_all([task, code])
    s.flush()
    try:
        yield World(s, TestClient(app), emp, boss, task, code)
    finally:
        app.dependency_overrides.clear()
        s.close()
        outer.rollback()
        conn.close()


def hdr(user: User) -> dict[str, str]:
    return {"X-User-Id": str(user.id)}


def add(w: World, minutes: int = 60, day: date = DAY, **target: int) -> int:
    """Add a time entry as the employee (default: on the task); returns the HTTP status."""
    body = {"work_date": day.isoformat(), "minutes": minutes, **(target or {"task_id": w.task.id})}
    status: int = w.client.post("/time/entries", json=body, headers=hdr(w.emp)).status_code
    return status


def week_json(w: World) -> dict[str, object]:
    res = w.client.get("/time/week", params={"on": DAY.isoformat()}, headers=hdr(w.emp))
    data: dict[str, object] = res.json()
    return data


def submit(w: World) -> int:
    """Submit the employee's week; returns the approval id."""
    start = str(week_json(w)["week_start"])
    assert w.client.post(f"/time/weeks/{start}/submit", headers=hdr(w.emp)).status_code == 200
    inbox = w.client.get("/approvals/inbox", headers=hdr(w.boss)).json()
    approval_id: int = inbox[-1]["approval_id"]
    return approval_id
