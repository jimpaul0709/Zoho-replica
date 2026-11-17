"""HR options on an approved week: send it back for re-approval, or let the employee edit it."""

from datetime import date, timedelta
from typing import Any

from conftest import DAY, World, add, hdr
from sqlalchemy import select
from test_hr import hr_person, locked_week

from workhub_api.models import Approval, User


def week(w: World, ws: date) -> dict[str, Any]:
    res = w.client.get("/time/week", params={"on": ws.isoformat()}, headers=hdr(w.emp))
    data: dict[str, Any] = res.json()
    return data


def hr_post(w: World, who: User | None, user_id: int, ws: date, what: str, body: Any) -> Any:
    headers = hdr(who) if who else {}
    return w.client.post(f"/hr/users/{user_id}/weeks/{ws}/{what}", json=body, headers=headers)


def two_day_week(w: World) -> tuple[date, date, date]:
    """An approved week with time on its first two days. Returns the week start and those days."""
    ws = DAY - timedelta(days=DAY.weekday())
    d0, d1 = ws, ws + timedelta(days=1)
    assert add(w, 60, day=d0) == 201 and add(w, 30, day=d1) == 201
    assert w.client.post(f"/time/weeks/{ws}/submit", headers=hdr(w.emp)).status_code == 200
    approval_id = w.client.get("/approvals/inbox", headers=hdr(w.boss)).json()[0]["approval_id"]
    assert (
        w.client.post(f"/approvals/{approval_id}/approve", headers=hdr(w.boss)).status_code == 200
    )
    return ws, d0, d1


def first_approval(w: World) -> int:
    approval_id = w.session.scalars(
        select(Approval.id).where(Approval.requester_id == w.emp.id).order_by(Approval.id)
    ).first()
    assert approval_id is not None
    return approval_id


def test_hr_sends_the_whole_week_back_and_the_manager_approves_it_again(world: World) -> None:
    hr = hr_person(world)
    ws, (e1, _) = locked_week(world)
    res = hr_post(world, hr, world.emp.id, ws, "send-back", {"reason": "Wrong project"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "draft" and data["locked"] is False
    assert data["day_status"] == {DAY.isoformat(): "sent_back"}
    assert data["day_reasons"] == {DAY.isoformat(): "Wrong project"}

    edit = world.client.patch(f"/time/entries/{e1}", json={"minutes": 45}, headers=hdr(world.emp))
    assert edit.status_code == 200  # the employee can fix it now
    assert world.client.post(f"/time/weeks/{ws}/submit", headers=hdr(world.emp)).status_code == 200
    row = world.client.get("/approvals/inbox", headers=hdr(world.boss)).json()[0]
    assert [d["status"] for d in row["days"]] == ["pending"]  # the manager decides again
    approve = world.client.post(f"/approvals/{row['approval_id']}/approve", headers=hdr(world.boss))
    assert approve.status_code == 200
    done = week(world, ws)
    assert done["status"] == "approved" and done["locked"] is True
    assert sorted(e["minutes"] for e in done["entries"]) == [30, 45]
    steps = world.client.get(f"/approvals/{first_approval(world)}/history", headers=hdr(world.emp))
    assert [s["action"] for s in steps.json()] == ["submitted", "approved", "hr_sent_back"]


def test_hr_sends_one_day_back_and_the_other_day_stays_locked(world: World) -> None:
    hr = hr_person(world)
    ws, d0, d1 = two_day_week(world)
    body = {"reason": "Fix day 2", "dates": [d1.isoformat()]}
    res = hr_post(world, hr, world.emp.id, ws, "send-back", body)
    assert res.status_code == 200
    assert res.json()["day_status"] == {d0.isoformat(): "approved", d1.isoformat(): "sent_back"}
    assert add(world, 5, day=d0) == 409  # still approved and locked
    assert add(world, 5, day=d1) == 201  # the returned day can be fixed
    assert world.client.post(f"/time/weeks/{ws}/submit", headers=hdr(world.emp)).status_code == 200
    row = world.client.get("/approvals/inbox", headers=hdr(world.boss)).json()[0]
    assert [d["status"] for d in row["days"]] == ["approved", "pending"]  # only d1 waits
    approve = world.client.post(f"/approvals/{row['approval_id']}/approve", headers=hdr(world.boss))
    assert approve.json()["status"] == "approved"
    assert week(world, ws)["status"] == "approved"


def test_hr_send_back_rules(world: World) -> None:
    hr = hr_person(world)
    ws, _, _ = two_day_week(world)
    body = {"reason": "x"}
    assert hr_post(world, None, world.emp.id, ws, "send-back", body).status_code == 401
    assert hr_post(world, world.emp, world.emp.id, ws, "send-back", body).status_code == 403
    assert hr_post(world, world.boss, world.emp.id, ws, "send-back", body).status_code == 403
    assert hr_post(world, hr, hr.id, ws, "send-back", body).status_code == 403  # their own week
    assert hr_post(world, hr, world.emp.id, ws, "send-back", {"reason": ""}).status_code == 422
    nothing = {"reason": "x", "dates": [(ws + timedelta(days=4)).isoformat()]}
    assert hr_post(world, hr, world.emp.id, ws, "send-back", nothing).status_code == 404
    assert week(world, ws)["status"] == "approved"  # nothing changed
    change = [{"op": "update", "entry_id": week(world, ws)["entries"][0]["id"], "minutes": 5}]
    filed = world.client.post(
        f"/time/weeks/{ws}/edit-requests",
        json={"reason": "r", "changes": change},
        headers=hdr(world.emp),
    )
    assert filed.status_code == 201
    assert hr_post(world, hr, world.emp.id, ws, "send-back", body).status_code == 409  # pending
    other = ws - timedelta(days=7)  # a week with nothing in it
    assert hr_post(world, hr, world.emp.id, other, "send-back", body).status_code == 409
