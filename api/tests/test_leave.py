"""Leave: types, balances, apply, approve, withdraw, cancel (leave.py)."""

from datetime import date, timedelta
from typing import Any

from conftest import World, hdr
from sqlalchemy import select
from test_hr import hr_person, locked_week

from workhub_api.leave import leave_year_of
from workhub_api.models import AuditEvent, User
from workhub_api.routing import org_settings

DAY_MIN = 480  # minutes, for time entries
H = 8  # hours, for leave


def monday() -> date:
    """A Monday in the future, so the weeks around it are empty."""
    today = date.today()
    return today + timedelta(days=7 - today.weekday())


def make_type(w: World, hr: User, name: str = "T-Earned", **fields: Any) -> int:
    body = {"name": name, "charge_code_id": w.code.id, **fields}
    res = w.client.post("/leave/types", json=body, headers=hdr(hr))
    assert res.status_code == 201, res.text
    type_id: int = res.json()["id"]
    return type_id


def give(w: World, hr: User, type_id: int, day: date, opening: int) -> None:
    year = leave_year_of(org_settings(w.session), day)
    body = {"user_id": w.emp.id, "leave_type_id": type_id, "leave_year": year, "opening": opening}
    assert w.client.put("/leave/balances", json=body, headers=hdr(hr)).status_code == 200


def apply(w: World, type_id: int, start: date, end: date, **extra: Any) -> Any:
    body = {
        "leave_type_id": type_id,
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        **extra,
    }
    return w.client.post("/leave/requests", json=body, headers=hdr(w.emp))


def balance(w: World, day: date) -> dict[str, Any]:
    year = leave_year_of(org_settings(w.session), day)
    rows = w.client.get("/leave/balances", params={"year": year}, headers=hdr(w.emp)).json()
    row: dict[str, Any] = rows[0]
    return row


def leave_entries(w: World, day: date) -> list[dict[str, Any]]:
    week = w.client.get("/time/week", params={"on": day.isoformat()}, headers=hdr(w.emp)).json()
    return [e for e in week["entries"] if e["source"] == "leave"]


def approve(w: World, approval_id: int) -> Any:
    return w.client.post(f"/approvals/{approval_id}/approve", headers=hdr(w.boss))


def test_apply_approve_writes_entries_and_deducts_then_cancel_reverses(world: World) -> None:
    w = world
    hr = hr_person(w)
    start = monday()
    type_id = make_type(w, hr)
    give(w, hr, type_id, start, 5 * H)

    res = apply(w, type_id, start, start + timedelta(days=2), reason="family")  # Mon to Wed
    assert res.status_code == 201, res.text
    request = res.json()
    assert request["hours"] == 3 * H and request["status"] == "applied"
    assert balance(w, start)["pending"] == 3 * H
    assert balance(w, start)["available"] == 2 * H
    assert leave_entries(w, start) == []  # nothing is written until it is approved

    inbox = w.client.get("/approvals/inbox", params={"subject_type": "leave"}, headers=hdr(w.boss))
    (item,) = inbox.json()
    assert item["leave"]["leave_type"] == "T-Earned" and item["leave"]["hours"] == 3 * H

    done = approve(w, request["approval_id"])
    assert done.status_code == 200 and done.json()["status"] == "approved"
    entries = leave_entries(w, start)
    assert [e["minutes"] for e in entries] == [DAY_MIN] * 3
    assert {e["charge_code_id"] for e in entries} == {w.code.id}
    after = balance(w, start)
    assert after["used"] == 3 * H and after["pending"] == 0
    assert after["available"] == 2 * H
    edit = w.client.patch(
        f"/time/entries/{entries[0]['id']}", json={"minutes": 5}, headers=hdr(w.emp)
    )
    assert edit.status_code == 409  # leave entries are read-only

    cancel = w.client.post(f"/leave/requests/{request['id']}/cancel", headers=hdr(w.emp))
    assert cancel.status_code == 200 and cancel.json()["status"] == "cancelled"
    assert leave_entries(w, start) == []
    assert balance(w, start)["used"] == 0 and balance(w, start)["available"] == 5 * H
    actions = set(
        w.session.scalars(select(AuditEvent.action).where(AuditEvent.entity == "leave_balance"))
    )
    assert {"set", "used", "restored"} <= actions


def test_half_days_count_half_and_balance_is_checked(world: World) -> None:
    w = world
    hr = hr_person(w)
    start = monday()
    type_id = make_type(w, hr)
    give(w, hr, type_id, start, 2 * H)

    half = {(start + timedelta(days=1)).isoformat(): "first_half"}
    ok = apply(w, type_id, start, start + timedelta(days=1), half_days=half)  # 1 + 0.5 days
    assert ok.status_code == 201 and ok.json()["hours"] == H + H / 2
    # only half a day is left, counting what is already waiting
    too_much = apply(w, type_id, start + timedelta(days=3), start + timedelta(days=4))
    assert too_much.status_code == 422 and "Not enough" in too_much.json()["detail"]
    other_day = {(start + timedelta(days=1)).isoformat(): "second_half"}
    stray = apply(w, type_id, start, start, half_days=other_day)
    assert stray.status_code == 422  # that half day is not in the range


def test_rules_at_apply_time(world: World) -> None:
    w = world
    hr = hr_person(w)
    start = monday()
    paid = make_type(w, hr, "T-Sick", attachment_after_days=1)
    lop = make_type(w, hr, "T-LOP", paid=False)
    give(w, hr, paid, start, 10 * H)

    assert apply(w, lop, start, start).status_code == 422  # LOP leave needs a reason
    assert apply(w, lop, start, start, reason="personal").status_code == 201  # no balance

    two_days = apply(w, paid, start + timedelta(days=1), start + timedelta(days=2))
    assert two_days.status_code == 422 and "attachment" in two_days.json()["detail"]
    with_file = apply(
        w, paid, start + timedelta(days=1), start + timedelta(days=2), attachment_key="doc-1"
    )
    assert with_file.status_code == 201

    saturday = start + timedelta(days=5)
    assert apply(w, paid, saturday, saturday + timedelta(days=1)).status_code == 422  # weekend
    assert apply(w, paid, start, start).status_code == 409  # already has leave that day
    assert apply(w, paid, start + timedelta(days=4), start - timedelta(days=1)).status_code == 422

    day = start + timedelta(days=4)
    black = w.client.post(
        "/leave/blackout-days",
        json={"on_date": day.isoformat(), "note": "Year-end"},
        headers=hdr(hr),
    )
    assert black.status_code == 201
    blocked = apply(w, paid, day, day)
    assert blocked.status_code == 422 and "Year-end" in blocked.json()["detail"]

    employee_only = w.client.post(
        "/leave/types", json={"name": "T-X", "charge_code_id": w.code.id}, headers=hdr(w.emp)
    )
    assert employee_only.status_code == 403
    assert w.client.get("/leave/types", headers=hdr(w.emp)).status_code == 200


def test_two_half_days_can_share_a_day(world: World) -> None:
    w = world
    hr = hr_person(w)
    start = monday()
    type_id = make_type(w, hr)
    give(w, hr, type_id, start, 5 * H)
    first = apply(w, type_id, start, start, half_days={start.isoformat(): "first_half"})
    second = apply(w, type_id, start, start, half_days={start.isoformat(): "second_half"})
    again = apply(w, type_id, start, start, half_days={start.isoformat(): "second_half"})
    assert first.status_code == 201 and second.status_code == 201
    assert again.status_code == 409


def test_withdraw_and_send_back_change_nothing(world: World) -> None:
    w = world
    hr = hr_person(w)
    start = monday()
    type_id = make_type(w, hr)
    give(w, hr, type_id, start, 5 * H)

    one = apply(w, type_id, start, start).json()
    withdrawn = w.client.post(f"/leave/requests/{one['id']}/withdraw", headers=hdr(w.emp))
    assert withdrawn.status_code == 200 and withdrawn.json()["status"] == "withdrawn"
    again = w.client.post(f"/leave/requests/{one['id']}/withdraw", headers=hdr(w.emp))
    assert again.status_code == 409
    assert approve(w, one["approval_id"]).status_code == 409  # the approval was cancelled with it

    two = apply(w, type_id, start, start).json()  # the same day is free again
    pinned = w.client.post(
        f"/approvals/{two['approval_id']}/send-back",
        json={"reason": "busy week", "entry_ids": [1]},
        headers=hdr(w.boss),
    )
    assert pinned.status_code == 422
    back = w.client.post(
        f"/approvals/{two['approval_id']}/send-back",
        json={"reason": "busy week"},
        headers=hdr(w.boss),
    )
    assert back.status_code == 200 and back.json()["status"] == "sent_back"
    mine = w.client.get("/leave/requests", headers=hdr(w.emp)).json()
    assert [r["status"] for r in mine] == ["rejected", "withdrawn"]
    assert leave_entries(w, start) == [] and balance(w, start)["used"] == 0
    history = w.client.get(f"/approvals/{two['approval_id']}/history", headers=hdr(w.emp)).json()
    assert [s["action"] for s in history] == ["submitted", "sent_back"]


def test_late_leave_is_flagged_and_bulk_approve_works(world: World) -> None:
    w = world
    hr = hr_person(w)
    past = monday() - timedelta(days=28)
    type_id = make_type(w, hr)
    give(w, hr, type_id, past, 5 * H)
    request = apply(w, type_id, past, past).json()
    assert request["applied_after_dates"] is True
    bulk = w.client.post(
        "/approvals/bulk-approve",
        json={"approval_ids": [request["approval_id"]]},
        headers=hdr(w.boss),
    )
    assert bulk.json() == {"approved": [request["approval_id"]], "skipped": []}
    assert len(leave_entries(w, past)) == 1


def test_approval_fails_if_the_week_is_already_approved_or_balance_is_gone(world: World) -> None:
    w = world
    hr = hr_person(w)
    week_start, _ = locked_week(w)  # an approved week in the past
    type_id = make_type(w, hr)
    give(w, hr, type_id, week_start, H)
    request = apply(w, type_id, week_start, week_start).json()
    res = approve(w, request["approval_id"])
    assert res.status_code == 409 and "already approved" in res.json()["detail"]
    assert balance(w, week_start)["used"] == 0  # nothing was deducted

    start = monday()
    give(w, hr, type_id, start, 2 * H)  # the first request still waits and counts too
    later = apply(w, type_id, start, start).json()
    give(w, hr, type_id, start, 0)  # HR lowers the balance while the request waits
    short = approve(w, later["approval_id"])
    assert short.status_code == 409 and "Not enough" in short.json()["detail"]
