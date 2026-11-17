"""HR direct correction of an approved week (hr.py)."""

from datetime import date, timedelta
from typing import Any

from conftest import DAY, World, add, hdr, submit, week_json
from sqlalchemy import select

from workhub_api.models import AuditEvent, RoleAssignment, User


def hr_person(w: World, code: str = "HR1") -> User:
    user = User(employee_code=code, name=code, email=f"{code.lower()}@x.io")
    w.session.add(user)
    w.session.flush()
    w.session.add(RoleAssignment(user_id=user.id, role="hr"))
    w.session.flush()
    return user


def locked_week(w: World) -> tuple[date, list[int]]:
    """An approved week with two entries (60 and 30 minutes). Returns its start and entry ids."""
    assert add(w, 60) == 201 and add(w, 30) == 201
    approval_id = submit(w)
    assert (
        w.client.post(f"/approvals/{approval_id}/approve", headers=hdr(w.boss)).status_code == 200
    )
    week = week_json(w)
    ids = [e["id"] for e in week["entries"]]  # type: ignore[attr-defined]
    return date.fromisoformat(str(week["week_start"])), ids


def correct(w: World, who: User | None, user_id: int, ws: date, body: dict[str, Any]) -> Any:
    headers = hdr(who) if who else {}
    return w.client.post(f"/hr/users/{user_id}/weeks/{ws}/corrections", json=body, headers=headers)


def test_hr_corrects_an_approved_week_and_the_audit_log_says_who_and_why(world: World) -> None:
    hr = hr_person(world)
    ws, (e1, e2) = locked_week(world)
    body = {
        "reason": "Entered 10 hours instead of 9",
        "changes": [
            {"op": "update", "entry_id": e1, "minutes": 120},
            {"op": "delete", "entry_id": e2},
            {
                "op": "add",
                "work_date": (ws + timedelta(days=2)).isoformat(),
                "minutes": 45,
                "task_id": world.task.id,
            },
        ],
    }
    res = correct(world, hr, world.emp.id, ws, body)
    assert res.status_code == 200
    week = res.json()
    assert sorted(e["minutes"] for e in week["entries"]) == [45, 120]
    assert week["status"] == "approved" and week["locked"] is True  # still locked afterwards
    assert sorted(e["minutes"] for e in week_json(world)["entries"]) == [45, 120]  # type: ignore[attr-defined]

    by_hr = set(
        world.session.scalars(
            select(AuditEvent.action).where(
                AuditEvent.entity == "time_entry", AuditEvent.actor_id == hr.id
            )
        )
    )
    assert by_hr == {"created", "updated", "deleted"}
    note = world.session.scalars(
        select(AuditEvent).where(AuditEvent.action == "hr_corrected", AuditEvent.actor_id == hr.id)
    ).one()
    assert note.after is not None and note.after["reason"] == "Entered 10 hours instead of 9"


def test_only_hr_can_correct_and_not_their_own_week(world: World) -> None:
    hr = hr_person(world)
    ws, (e1, _) = locked_week(world)
    body = {"reason": "x", "changes": [{"op": "update", "entry_id": e1, "minutes": 5}]}
    assert correct(world, None, world.emp.id, ws, body).status_code == 401
    assert correct(world, world.emp, world.emp.id, ws, body).status_code == 403  # an employee
    assert correct(world, world.boss, world.emp.id, ws, body).status_code == 403  # a manager
    assert correct(world, hr, hr.id, ws, body).status_code == 403  # their own week
    assert sorted(e["minutes"] for e in week_json(world)["entries"]) == [30, 60]  # type: ignore[attr-defined]


def test_only_an_approved_week_that_exists(world: World) -> None:
    hr = hr_person(world)
    assert add(world, 60) == 201  # a draft week
    ws = date.fromisoformat(str(week_json(world)["week_start"]))
    body = {"reason": "x", "changes": [{"op": "delete", "entry_id": 1}]}
    assert correct(world, hr, world.emp.id, ws, body).status_code == 409  # not approved
    assert correct(world, hr, world.emp.id, ws - timedelta(days=7), body).status_code == 409
    assert correct(world, hr, world.emp.id, ws + timedelta(days=1), body).status_code == 422
    assert correct(world, hr, 999999999, ws, body).status_code == 404


def test_a_bad_correction_changes_nothing(world: World) -> None:
    hr = hr_person(world)
    ws, (e1, e2) = locked_week(world)
    day = DAY.isoformat()  # the day that already has 90 minutes
    too_much = {"op": "add", "work_date": day, "minutes": 1400, "task_id": world.task.id}
    res = correct(world, hr, world.emp.id, ws, {"reason": "x", "changes": [too_much]})
    assert res.status_code == 422  # over 24 hours
    ok_then_bad = [
        {"op": "update", "entry_id": e1, "minutes": 5},
        {"op": "delete", "entry_id": 999},
    ]
    res = correct(world, hr, world.emp.id, ws, {"reason": "x", "changes": ok_then_bad})
    assert res.status_code == 422
    assert sorted(e["minutes"] for e in week_json(world)["entries"]) == [30, 60]  # type: ignore[attr-defined]
    assert (
        correct(world, hr, world.emp.id, ws, {"reason": "", "changes": ok_then_bad}).status_code
        == 422
    )
    assert correct(world, hr, world.emp.id, ws, {"reason": "x", "changes": []}).status_code == 422


def test_a_pending_edit_request_blocks_a_correction(world: World) -> None:
    hr = hr_person(world)
    ws, (e1, _) = locked_week(world)
    change = [{"op": "update", "entry_id": e1, "minutes": 90}]
    filed = world.client.post(
        f"/time/weeks/{ws}/edit-requests",
        json={"reason": "mine", "changes": change},
        headers=hdr(world.emp),
    )
    assert filed.status_code == 201
    res = correct(world, hr, world.emp.id, ws, {"reason": "x", "changes": change})
    assert res.status_code == 409
