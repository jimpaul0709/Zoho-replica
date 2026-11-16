"""Per-day approval: the manager decides a whole week or one day at a time (day_decisions.py)."""

from datetime import date, timedelta
from typing import Any

from conftest import DAY, World, add, hdr

from workhub_api.models import RoleAssignment, User


def d(n: int) -> date:
    """Day n of the test week (0 is its first day)."""
    return DAY - timedelta(days=DAY.weekday()) + timedelta(days=n)


def week(w: World) -> dict[str, Any]:
    res = w.client.get("/time/week", params={"on": d(0).isoformat()}, headers=hdr(w.emp))
    data: dict[str, Any] = res.json()
    return data


def submit(w: World) -> int:
    assert w.client.post(f"/time/weeks/{d(0)}/submit", headers=hdr(w.emp)).status_code == 200
    return int(inbox(w)[0]["approval_id"])


def inbox(w: World) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = w.client.get("/approvals/inbox", headers=hdr(w.boss)).json()
    return rows


def day_act(
    w: World, ap: int, day: date, action: str, user: User | None = None, **body: Any
) -> Any:
    url = f"/approvals/{ap}/days/{day.isoformat()}/{action}"
    return w.client.post(url, json=body or None, headers=hdr(user or w.boss))


def history(w: World, ap: int) -> list[str]:
    steps = w.client.get(f"/approvals/{ap}/history", headers=hdr(w.emp)).json()
    return [s["action"] for s in steps]


def log_days(w: World, *minutes: int) -> None:
    for n, m in enumerate(minutes):
        assert add(w, m, day=d(n)) == 201


def entry_on(w: World, day: date) -> int:
    return int(next(e["id"] for e in week(w)["entries"] if e["work_date"] == day.isoformat()))


def test_approve_day_by_day_then_the_week_closes(world: World) -> None:
    log_days(world, 60, 90, 30)
    ap = submit(world)
    row = inbox(world)[0]
    assert [(x["work_date"], x["minutes"], x["status"]) for x in row["days"]] == [
        (d(0).isoformat(), 60, "pending"),
        (d(1).isoformat(), 90, "pending"),
        (d(2).isoformat(), 30, "pending"),
    ]
    assert row["total_minutes"] == 180

    res = day_act(world, ap, d(0), "approve")
    assert res.status_code == 200 and res.json()["status"] == "pending"  # other days still wait
    wk = week(world)
    assert wk["status"] == "submitted" and wk["locked"] is False
    assert wk["day_status"] == {
        d(0).isoformat(): "approved",
        d(1).isoformat(): "submitted",
        d(2).isoformat(): "submitted",
    }
    assert wk["approved_minutes"] == 60

    first, second = entry_on(world, d(0)), entry_on(world, d(1))
    patch = world.client.patch(
        f"/time/entries/{first}", json={"minutes": 5}, headers=hdr(world.emp)
    )
    assert patch.status_code == 409  # an approved day is locked
    assert world.client.delete(f"/time/entries/{first}", headers=hdr(world.emp)).status_code == 409
    assert add(world, 5, day=d(0)) == 409
    edit = world.client.patch(
        f"/time/entries/{second}", json={"minutes": 100}, headers=hdr(world.emp)
    )
    assert edit.status_code == 200  # the other days can still be edited

    assert day_act(world, ap, d(0), "approve").status_code == 409  # already decided
    assert day_act(world, ap, d(5), "approve").status_code == 404  # nothing logged that day
    assert day_act(world, ap, d(1), "approve").json()["status"] == "pending"
    last = day_act(world, ap, d(2), "approve")
    assert last.status_code == 200 and last.json()["status"] == "approved"  # the last day closes it
    wk = week(world)
    assert wk["status"] == "approved" and wk["locked"] is True
    assert wk["approved_minutes"] == 60 + 100 + 30
    assert history(world, ap) == [
        "submitted",
        "day_approved",
        "day_approved",
        "day_approved",
        "approved",
    ]
    assert inbox(world) == []


def test_send_back_one_day_and_resubmit_only_that_day(world: World) -> None:
    log_days(world, 60, 90, 30)
    ap = submit(world)
    assert day_act(world, ap, d(0), "approve").status_code == 200
    bad = entry_on(world, d(1))
    sent = day_act(world, ap, d(1), "send-back", reason="Wrong project", entry_ids=[bad])
    assert sent.status_code == 200 and sent.json()["status"] == "pending"  # one day still waits
    closed = day_act(world, ap, d(2), "approve")
    assert closed.json()["status"] == "sent_back"  # every day decided, one sent back
    assert "Wrong project" in closed.json()["reason"]

    wk = week(world)
    assert wk["status"] == "draft"
    assert wk["day_status"] == {
        d(0).isoformat(): "approved",
        d(1).isoformat(): "sent_back",
        d(2).isoformat(): "approved",
    }
    assert [e["sent_back_reason"] for e in wk["entries"] if e["id"] == bad] == ["Wrong project"]
    assert add(world, 5, day=d(0)) == 409  # approved days stay locked
    fix = world.client.patch(f"/time/entries/{bad}", json={"minutes": 45}, headers=hdr(world.emp))
    assert fix.status_code == 200  # the sent-back day can be fixed

    new = submit(world)  # resubmit
    assert new != ap
    row = inbox(world)[0]
    assert [x["status"] for x in row["days"]] == ["approved", "pending", "approved"]  # one waits
    assert day_act(world, new, d(1), "approve").json()["status"] == "approved"
    wk = week(world)
    assert wk["status"] == "approved" and wk["locked"] is True and wk["approved_minutes"] == 135
    assert history(world, ap) == [
        "submitted",
        "day_approved",
        "day_sent_back",
        "day_approved",
        "sent_back",
    ]
    assert history(world, new) == ["submitted", "day_approved", "approved"]


def test_sending_the_whole_week_back_works_like_a_day_and_resubmits(world: World) -> None:
    log_days(world, 60, 90)
    ap = submit(world)
    assert day_act(world, ap, d(0), "approve").status_code == 200
    back = world.client.post(
        f"/approvals/{ap}/send-back", json={"reason": "Please redo"}, headers=hdr(world.boss)
    )
    assert back.status_code == 200 and back.json()["status"] == "sent_back"
    wk = week(world)
    assert wk["status"] == "draft"
    assert wk["day_status"] == {d(0).isoformat(): "approved", d(1).isoformat(): "sent_back"}

    new = submit(world)  # only the sent-back day goes back to the manager
    assert [x["status"] for x in inbox(world)[0]["days"]] == ["approved", "pending"]
    done = world.client.post(f"/approvals/{new}/approve", headers=hdr(world.boss))
    assert done.status_code == 200 and done.json()["status"] == "approved"
    assert week(world)["status"] == "approved"


def test_approving_the_whole_week_when_a_day_was_sent_back(world: World) -> None:
    log_days(world, 60, 90, 30)
    ap = submit(world)
    assert day_act(world, ap, d(1), "send-back", reason="No").status_code == 200
    done = world.client.post(f"/approvals/{ap}/approve", headers=hdr(world.boss))
    assert done.status_code == 200 and done.json()["status"] == "sent_back"  # the returned day
    wk = week(world)
    assert wk["status"] == "draft"
    assert wk["day_status"] == {
        d(0).isoformat(): "approved",
        d(1).isoformat(): "sent_back",
        d(2).isoformat(): "approved",
    }


def test_bulk_approve_finishes_the_days_still_waiting(world: World) -> None:
    log_days(world, 60, 90)
    ap = submit(world)
    assert day_act(world, ap, d(0), "approve").status_code == 200
    res = world.client.post(
        "/approvals/bulk-approve", json={"approval_ids": [ap]}, headers=hdr(world.boss)
    )
    assert res.json() == {"approved": [ap], "skipped": []}
    wk = week(world)
    assert wk["status"] == "approved" and wk["approved_minutes"] == 150


def test_day_decision_rules(world: World) -> None:
    log_days(world, 60, 90)
    ap = submit(world)
    emp = day_act(world, ap, d(0), "approve", user=world.emp)
    assert emp.status_code == 403  # an employee can't decide
    other = User(employee_code="M2", name="M2", email="m2@x.io")
    world.session.add(other)
    world.session.flush()
    world.session.add(RoleAssignment(user_id=other.id, role="manager"))
    world.session.flush()
    assert day_act(world, ap, d(0), "approve", user=other).status_code == 404  # not their approval
    assert day_act(world, ap, d(0), "send-back", reason="").status_code == 422  # a reason is needed
    elsewhere = entry_on(world, d(1))  # an entry of another day
    wrong = day_act(world, ap, d(0), "send-back", reason="x", entry_ids=[elsewhere])
    assert wrong.status_code == 422
    assert day_act(world, ap, d(0), "send-back", reason="x").status_code == 200
    assert day_act(world, ap, d(0), "approve").status_code == 409  # already sent back
