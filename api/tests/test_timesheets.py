from datetime import date, timedelta

from conftest import DAY, World, add, hdr, week_json
from sqlalchemy import select

from workhub_api.models import Approval, AuditEvent, ChargeCodeTeam, Team, TeamMember


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
