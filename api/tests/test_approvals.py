from conftest import World, add, hdr, submit, week_json
from sqlalchemy import select

from workhub_api.models import Approval, AuditEvent, RoleAssignment, User


def test_inbox_lists_submitted_week(world: World) -> None:
    add(world, 90)
    add(world, 30)
    submit(world)
    inbox = world.client.get("/approvals/inbox", headers=hdr(world.boss)).json()
    assert len(inbox) == 1
    assert inbox[0]["requester_name"] == "Emp" and inbox[0]["total_minutes"] == 120
    assert world.client.get("/approvals/inbox", headers=hdr(world.emp)).json() == []


def test_approve_locks_the_week_and_records_history(world: World) -> None:
    add(world)
    approval_id = submit(world)
    res = world.client.post(f"/approvals/{approval_id}/approve", headers=hdr(world.boss))
    assert res.status_code == 200 and res.json()["status"] == "approved"
    week = week_json(world)
    assert week["status"] == "approved" and week["locked"] is True
    assert add(world, 30) == 409  # a locked week can't be changed
    steps = world.client.get(f"/approvals/{approval_id}/history", headers=hdr(world.emp)).json()
    assert [s["action"] for s in steps] == ["submitted", "approved"]
    actions = world.session.scalars(
        select(AuditEvent.action).where(
            AuditEvent.entity == "timesheet_week", AuditEvent.actor_id == world.boss.id
        )
    ).all()
    assert "approved" in actions


def test_send_back_pins_reason_and_reopens_week(world: World) -> None:
    add(world, 60)
    approval_id = submit(world)
    entries: list[dict[str, int]] = week_json(world)["entries"]  # type: ignore[assignment]
    res = world.client.post(
        f"/approvals/{approval_id}/send-back",
        json={"reason": "Wrong project", "entry_ids": [entries[0]["id"]]},
        headers=hdr(world.boss),
    )
    assert res.status_code == 200 and res.json()["status"] == "sent_back"
    week = week_json(world)
    assert week["status"] == "draft"
    assert week["entries"][0]["sent_back_reason"] == "Wrong project"  # type: ignore[index]
    assert add(world, 30) == 201  # the employee can fix the week again
    # Resubmitting creates a fresh approval; the sent-back one stays in the history.
    second = submit(world)
    assert second != approval_id
    mine = select(Approval).where(Approval.requester_id == world.emp.id)
    assert len(world.session.scalars(mine).all()) == 2


def test_only_the_approver_can_act_and_only_once(world: World) -> None:
    add(world)
    approval_id = submit(world)
    url = f"/approvals/{approval_id}"
    assert world.client.post(f"{url}/approve", headers=hdr(world.emp)).status_code == 403  # no role
    other = User(employee_code="M2", name="M2", email="m2@x.io")  # a manager, but not this one's
    world.session.add(other)
    world.session.flush()
    world.session.add(RoleAssignment(user_id=other.id, role="manager"))
    world.session.flush()
    assert world.client.post(f"{url}/approve", headers=hdr(other)).status_code == 404
    assert world.client.post(f"{url}/approve", headers=hdr(world.boss)).status_code == 200
    assert world.client.post(f"{url}/approve", headers=hdr(world.boss)).status_code == 409


def test_send_back_needs_a_reason_and_this_weeks_entries(world: World) -> None:
    add(world)
    approval_id = submit(world)
    url = f"/approvals/{approval_id}/send-back"
    assert world.client.post(url, json={"reason": ""}, headers=hdr(world.boss)).status_code == 422
    bad = world.client.post(
        url, json={"reason": "x", "entry_ids": [999999999]}, headers=hdr(world.boss)
    )
    assert bad.status_code == 422
    # The approval is still pending after the rejected attempts.
    assert world.client.get("/approvals/inbox", headers=hdr(world.boss)).json() != []
