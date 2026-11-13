from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from workhub_api.config import settings
from workhub_api.db import engine, get_session
from workhub_api.main import app
from workhub_api.models import (
    Approval,
    AuditEvent,
    ChargeCode,
    ChargeCodeTeam,
    Project,
    Task,
    TaskList,
    TaskStatus,
    Team,
    TeamMember,
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
    """App wired to one session inside a transaction that is rolled back, so nothing is kept."""
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
    code = ChargeCode(code="Bench", name="Bench")
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
    body = {"work_date": day.isoformat(), "minutes": minutes, **(target or {"task_id": w.task.id})}
    status: int = w.client.post("/time/entries", json=body, headers=hdr(w.emp)).status_code
    return status


def week_json(w: World) -> dict[str, object]:
    res = w.client.get("/time/week", params={"on": DAY.isoformat()}, headers=hdr(w.emp))
    data: dict[str, object] = res.json()
    return data


def test_needs_a_user(world: World) -> None:
    assert world.client.get("/time/week").status_code == 401


def test_add_entry_and_week_view(world: World) -> None:
    assert add(world, 90) == 201
    assert add(world, 30) == 201
    data = week_json(world)
    assert data["status"] == "draft" and len(data["entries"]) == 2  # type: ignore[arg-type]
    assert data["day_minutes"][DAY.isoformat()] == 120  # type: ignore[index]
    assert date.fromisoformat(str(data["week_start"])).weekday() == 0  # Monday by default


def test_rules(world: World) -> None:
    assert add(world, 60, day=date.today() + timedelta(days=1)) == 422  # future
    assert add(world, 1000) == 201
    assert add(world, 500) == 422  # 1500 min is over 24 h
    assert add(world, 60, task_id=world.task.id, charge_code_id=world.code.id) == 422
    body = {"work_date": DAY.isoformat(), "minutes": 5}
    assert world.client.post("/time/entries", json=body, headers=hdr(world.emp)).status_code == 422


def test_charge_code_must_be_shared_with_users_team(world: World) -> None:
    assert add(world, 30, charge_code_id=world.code.id) == 422
    team = Team(name="Delivery")
    world.session.add(team)
    world.session.flush()
    world.session.add_all(
        [
            TeamMember(team_id=team.id, user_id=world.emp.id),
            ChargeCodeTeam(charge_code_id=world.code.id, team_id=team.id),
        ]
    )
    world.session.flush()
    assert add(world, 30, charge_code_id=world.code.id) == 201


def test_edit_delete_and_ownership(world: World) -> None:
    add(world, 60)
    entries: list[dict[str, int]] = week_json(world)["entries"]  # type: ignore[assignment]
    url = f"/time/entries/{entries[0]['id']}"
    edited = world.client.patch(url, json={"minutes": 45}, headers=hdr(world.emp))
    assert edited.json()["minutes"] == 45
    assert world.client.patch(url, json={"minutes": 5}, headers=hdr(world.boss)).status_code == 404
    assert world.client.delete(url, headers=hdr(world.emp)).status_code == 204
    actions = world.session.scalars(
        select(AuditEvent.action).where(AuditEvent.entity == "time_entry").order_by(AuditEvent.id)
    ).all()
    assert list(actions) == ["created", "updated", "deleted"]


def test_submit_creates_approval_and_locks_edits(world: World) -> None:
    assert add(world, 60) == 201
    start = str(week_json(world)["week_start"])
    res = world.client.post(f"/time/weeks/{start}/submit", headers=hdr(world.emp))
    assert res.status_code == 200 and res.json()["status"] == "submitted"
    approval = world.session.scalars(select(Approval)).one()
    assert approval.approver_id == world.boss.id and approval.status == "pending"
    assert add(world, 30) == 409  # submitted weeks can't be changed
    again = world.client.post(f"/time/weeks/{start}/submit", headers=hdr(world.emp))
    assert again.status_code == 409
