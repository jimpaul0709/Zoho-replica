from datetime import UTC, date, datetime, timedelta

from conftest import DAY, World, hdr
from sqlalchemy import select

from workhub_api.models import Approval, User


def person(w: World, code: str, manager: User | None) -> User:
    user = User(
        employee_code=code,
        name=code,
        email=f"{code.lower()}@x.io",
        manager_id=manager.id if manager else None,
    )
    w.session.add(user)
    w.session.flush()
    return user


def submit_as(w: World, user: User, day: date = DAY) -> int:
    """Log an hour and submit the week as `user`. Returns the approval id."""
    body = {"work_date": day.isoformat(), "minutes": 60, "task_id": w.task.id}
    assert w.client.post("/time/entries", json=body, headers=hdr(user)).status_code == 201
    week = w.client.get("/time/week", params={"on": day.isoformat()}, headers=hdr(user)).json()
    start = week["week_start"]
    assert w.client.post(f"/time/weeks/{start}/submit", headers=hdr(user)).status_code == 200
    approval_id = w.session.scalars(
        select(Approval.id).where(Approval.requester_id == user.id).order_by(Approval.id.desc())
    ).first()
    assert approval_id is not None
    return approval_id


def inbox_ids(w: World, who: User, **params: object) -> list[int]:
    res = w.client.get("/approvals/inbox", params=params, headers=hdr(who))
    assert res.status_code == 200
    return [row["approval_id"] for row in res.json()]


def test_inbox_row_shows_age_due_level_and_timeline(world: World) -> None:
    submit_as(world, world.emp)
    row = world.client.get("/approvals/inbox", headers=hdr(world.boss)).json()[0]
    assert row["requester_name"] == "Emp" and row["total_minutes"] == 60
    assert row["level"] == 1 and row["overdue"] is False and row["age_hours"] >= 0
    assert row["due_at"] is not None and row["week_start"] is not None
    assert [
        (s["action"], s["actor_name"], s["minutes_since_previous"]) for s in row["timeline"]
    ] == [("submitted", "Emp", None)]
    # After a delegation the trail grows, and the delegate sees the whole trail.
    deputy = person(world, "DEP", None)
    body = {
        "to_user_id": deputy.id,
        "starts_on": date.today().isoformat(),
        "ends_on": (date.today() + timedelta(days=3)).isoformat(),
    }
    assert world.client.post("/delegations", json=body, headers=hdr(world.boss)).status_code == 201
    row = world.client.get("/approvals/inbox", headers=hdr(deputy)).json()[0]
    steps = row["timeline"]
    assert [s["action"] for s in steps] == ["submitted", "delegated"]
    assert steps[1]["actor_name"] == "Boss" and isinstance(steps[1]["minutes_since_previous"], int)


def test_filters_and_sorting(world: World) -> None:
    other = person(world, "E2", world.boss)
    third = person(world, "E3", world.boss)
    a1 = submit_as(world, world.emp)
    a2 = submit_as(world, other)
    a3 = submit_as(world, third)
    overdue = world.session.get(Approval, a2)
    assert overdue is not None
    overdue.due_at = datetime.now(UTC) - timedelta(hours=1)
    world.session.flush()

    assert inbox_ids(world, world.boss) == [a1, a2, a3]  # oldest first
    assert inbox_ids(world, world.boss, sort="newest") == [a3, a2, a1]
    assert inbox_ids(world, world.boss, sort="due")[0] == a2  # the overdue one is first
    assert inbox_ids(world, world.boss, requester_id=other.id) == [a2]
    assert inbox_ids(world, world.boss, overdue="true") == [a2]
    assert inbox_ids(world, world.boss, subject_type="week") == [a1, a2, a3]
    assert inbox_ids(world, world.boss, subject_type="leave") == []
    bad = world.client.get("/approvals/inbox", params={"sort": "sideways"}, headers=hdr(world.boss))
    assert bad.status_code == 422


def test_bulk_approve_skips_what_it_cannot_approve_and_does_the_rest(world: World) -> None:
    other = person(world, "E2", world.boss)
    stranger = person(world, "E3", person(world, "BOSS2", None))  # reports to someone else
    a1 = submit_as(world, world.emp)
    a2 = submit_as(world, other)
    a3 = submit_as(world, stranger)
    res = world.client.post(
        "/approvals/bulk-approve",
        json={
            "approval_ids": [999999999, a1, a2, a3, a1]
        },  # an unknown id, one not theirs, a repeat
        headers=hdr(world.boss),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["approved"] == [a1, a2]
    assert [(s["approval_id"], s["reason"]) for s in data["skipped"]] == [
        (999999999, "Approval not found"),
        (a3, "Approval not found"),
    ]
    week = world.client.get("/time/week", params={"on": DAY.isoformat()}, headers=hdr(world.emp))
    assert week.json()["status"] == "approved" and week.json()["locked"] is True
    steps = world.client.get(f"/approvals/{a1}/history", headers=hdr(world.emp)).json()
    assert [s["action"] for s in steps] == ["submitted", "approved"]
    assert inbox_ids(world, world.boss) == []
    again = world.client.post(
        "/approvals/bulk-approve", json={"approval_ids": [a1]}, headers=hdr(world.boss)
    ).json()
    assert again["approved"] == [] and again["skipped"][0]["reason"] == "Already approved"
    empty = world.client.post(
        "/approvals/bulk-approve", json={"approval_ids": []}, headers=hdr(world.boss)
    )
    assert empty.status_code == 422


def test_whoever_acted_can_still_read_the_history(world: World) -> None:
    approval_id = submit_as(world, world.emp)
    deputy = person(world, "DEP", None)
    stranger = person(world, "NOSY", None)
    body = {
        "to_user_id": deputy.id,
        "starts_on": date.today().isoformat(),
        "ends_on": date.today().isoformat(),
    }
    world.client.post("/delegations", json=body, headers=hdr(world.boss))
    url = f"/approvals/{approval_id}/history"
    assert world.client.get(url, headers=hdr(world.boss)).status_code == 200  # delegated it away
    assert world.client.get(url, headers=hdr(deputy)).status_code == 200  # holds it now
    assert world.client.get(url, headers=hdr(stranger)).status_code == 404
