from datetime import date, timedelta

from conftest import DAY, World, add, hdr, submit, week_json
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
        select(AuditEvent.action)
        .where(AuditEvent.entity == "time_entry", AuditEvent.actor_id == world.emp.id)
        .order_by(AuditEvent.id)
    ).all()
    assert list(actions) == ["created", "updated", "deleted"]


def test_submit_creates_an_approval_for_the_manager(world: World) -> None:
    assert add(world, 60) == 201
    start = str(week_json(world)["week_start"])
    res = world.client.post(f"/time/weeks/{start}/submit", headers=hdr(world.emp))
    assert res.status_code == 200 and res.json()["status"] == "submitted"
    approval = world.session.scalars(
        select(Approval).where(Approval.requester_id == world.emp.id)
    ).one()
    assert approval.approver_id == world.boss.id and approval.status == "pending"
    again = world.client.post(f"/time/weeks/{start}/submit", headers=hdr(world.emp))
    assert again.status_code == 409


def test_a_submitted_week_can_be_edited_until_it_is_approved(world: World) -> None:
    assert add(world, 60) == 201
    approval_id = submit(world)
    assert add(world, 30) == 201  # still editable while it waits for the manager
    week = week_json(world)
    assert week["status"] == "submitted"
    first, second = (e["id"] for e in week["entries"])  # type: ignore[attr-defined]
    url = f"/time/entries/{first}"
    assert world.client.patch(url, json={"minutes": 45}, headers=hdr(world.emp)).status_code == 200
    assert world.client.delete(f"/time/entries/{second}", headers=hdr(world.emp)).status_code == 204
    row = world.client.get("/approvals/inbox", headers=hdr(world.boss)).json()[0]
    assert row["total_minutes"] == 45  # the manager sees what is there now
    approve = world.client.post(f"/approvals/{approval_id}/approve", headers=hdr(world.boss))
    assert approve.status_code == 200
    assert add(world, 5) == 409  # approved: locked
    assert world.client.patch(url, json={"minutes": 5}, headers=hdr(world.emp)).status_code == 409
    assert world.client.delete(url, headers=hdr(world.emp)).status_code == 409


def test_a_week_emptied_after_submit_cannot_be_approved(world: World) -> None:
    assert add(world, 60) == 201
    approval_id = submit(world)
    entry_id = week_json(world)["entries"][0]["id"]  # type: ignore[index]
    assert (
        world.client.delete(f"/time/entries/{entry_id}", headers=hdr(world.emp)).status_code == 204
    )
    url = f"/approvals/{approval_id}/approve"
    assert world.client.post(url, headers=hdr(world.boss)).status_code == 409
    assert add(world, 60) == 201  # the employee adds something again
    assert world.client.post(url, headers=hdr(world.boss)).status_code == 200
