from datetime import date, timedelta
from typing import Any

from conftest import World, add, hdr, week_json
from sqlalchemy import select

from workhub_api.models import AuditEvent, TimeEntry, TimesheetWeek, User


class Locked:
    """A week that is approved and locked: two entries on DAY (60 and 30 minutes)."""

    def __init__(self, w: World) -> None:
        self.w = w
        assert add(w, 60) == 201 and add(w, 30) == 201
        self.ws = date.fromisoformat(str(week_json(w)["week_start"]))
        self.e1, self.e2 = (e["id"] for e in self.entries())
        start = self.ws.isoformat()
        assert w.client.post(f"/time/weeks/{start}/submit", headers=hdr(w.emp)).status_code == 200
        inbox = w.client.get("/approvals/inbox", headers=hdr(w.boss)).json()
        res = w.client.post(f"/approvals/{inbox[-1]['approval_id']}/approve", headers=hdr(w.boss))
        assert res.status_code == 200

    def entries(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = week_json(self.w)["entries"]  # type: ignore[assignment]
        return entries

    def file(self, changes: list[dict[str, Any]], reason: str = "Fix hours") -> Any:
        return self.w.client.post(
            f"/time/weeks/{self.ws}/edit-requests",
            json={"reason": reason, "changes": changes},
            headers=hdr(self.w.emp),
        )

    def usual_changes(self) -> list[dict[str, Any]]:
        return [
            {"op": "update", "entry_id": self.e1, "minutes": 120},
            {"op": "delete", "entry_id": self.e2},
            {
                "op": "add",
                "work_date": (self.ws + timedelta(days=2)).isoformat(),
                "minutes": 45,
                "task_id": self.w.task.id,
            },
        ]

    def approval_id(self) -> int:
        inbox = self.w.client.get("/approvals/inbox", headers=hdr(self.w.boss)).json()
        return int(inbox[-1]["approval_id"])


def minutes_by_entry(locked: Locked) -> dict[int, int]:
    return {e["id"]: e["minutes"] for e in locked.entries()}


def test_only_a_locked_week_can_have_an_edit_request(world: World) -> None:
    add(world)  # a draft week
    ws = date.fromisoformat(str(week_json(world)["week_start"]))
    change = [{"op": "delete", "entry_id": 1}]
    url = f"/time/weeks/{ws}/edit-requests"
    body = {"reason": "x", "changes": change}
    assert world.client.post(url, json=body, headers=hdr(world.emp)).status_code == 409
    other = f"/time/weeks/{ws - timedelta(days=7)}/edit-requests"  # a week with nothing in it
    assert world.client.post(other, json=body, headers=hdr(world.emp)).status_code == 409
    mid = f"/time/weeks/{ws + timedelta(days=1)}/edit-requests"  # not the first day of a week
    assert world.client.post(mid, json=body, headers=hdr(world.emp)).status_code == 422


def test_filing_makes_a_pending_approval_and_changes_nothing_yet(world: World) -> None:
    locked = Locked(world)
    res = locked.file(locked.usual_changes())
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "pending" and data["approval_id"] is not None
    assert minutes_by_entry(locked) == {locked.e1: 60, locked.e2: 30}  # nothing applied
    week = week_json(world)
    assert week["status"] == "approved" and week["locked"] is True
    row = world.client.get("/approvals/inbox", headers=hdr(world.boss)).json()[0]
    assert row["subject_type"] == "edit_request" and row["week_start"] == locked.ws.isoformat()
    assert row["due_at"] is not None and row["timeline"][0]["comment"] == "Fix hours"
    assert add(world, 5) == 409  # the week is still locked for direct edits
    assert locked.file(locked.usual_changes()).status_code == 409  # one pending request at a time
    mine = world.client.get("/time/edit-requests", headers=hdr(world.emp)).json()
    assert [r["id"] for r in mine] == [data["id"]]


def test_approving_applies_every_change_and_keeps_the_week_locked(world: World) -> None:
    locked = Locked(world)
    request_id = locked.file(locked.usual_changes()).json()["id"]
    res = world.client.post(f"/approvals/{locked.approval_id()}/approve", headers=hdr(world.boss))
    assert res.status_code == 200 and res.json()["status"] == "approved"
    entries = locked.entries()
    by_id = {e["id"]: e for e in entries}
    assert by_id[locked.e1]["minutes"] == 120 and locked.e2 not in by_id
    added = [e for e in entries if e["id"] not in (locked.e1, locked.e2)]
    assert [(e["minutes"], e["source"]) for e in added] == [(45, "manual")]
    week = week_json(world)
    assert week["status"] == "approved" and week["locked"] is True  # still locked afterwards
    detail = world.client.get(f"/time/edit-requests/{request_id}", headers=hdr(world.boss)).json()
    assert detail["status"] == "approved"
    audit = world.session.scalars(
        select(AuditEvent.action).where(
            AuditEvent.entity == "time_entry", AuditEvent.actor_id == world.boss.id
        )
    ).all()
    assert {"created", "updated", "deleted"} <= set(audit)  # recorded against the approver
    assert locked.file(locked.usual_changes()[:1]).status_code == 201  # a new request is possible


def test_sending_back_rejects_the_request_and_leaves_the_week_alone(world: World) -> None:
    locked = Locked(world)
    locked.file(locked.usual_changes())
    approval_id = locked.approval_id()
    url = f"/approvals/{approval_id}/send-back"
    pin = {"reason": "No", "entry_ids": [locked.e1]}
    assert world.client.post(url, json=pin, headers=hdr(world.boss)).status_code == 422
    res = world.client.post(url, json={"reason": "Not needed"}, headers=hdr(world.boss))
    assert res.status_code == 200 and res.json()["status"] == "sent_back"
    request = world.client.get("/time/edit-requests", headers=hdr(world.emp)).json()[0]
    assert request["status"] == "rejected"
    assert minutes_by_entry(locked) == {locked.e1: 60, locked.e2: 30}
    assert week_json(world)["locked"] is True
    assert locked.file(locked.usual_changes()[:1]).status_code == 201  # may ask again


def test_bad_requests_are_refused_up_front_and_nothing_is_created(world: World) -> None:
    locked = Locked(world)
    week = world.session.scalars(
        select(TimesheetWeek).where(TimesheetWeek.user_id == world.emp.id)
    ).one()
    leave = TimeEntry(
        user_id=world.emp.id,
        week_id=week.id,
        work_date=locked.ws + timedelta(days=4),
        minutes=480,
        task_id=world.task.id,
        source="leave",
    )
    world.session.add(leave)
    world.session.flush()
    day2 = (locked.ws + timedelta(days=2)).isoformat()
    before_week = (locked.ws - timedelta(days=1)).isoformat()
    bad: dict[str, list[dict[str, Any]]] = {
        "unknown entry": [{"op": "delete", "entry_id": 999999999}],
        "over 24 hours": [{"op": "update", "entry_id": locked.e1, "minutes": 1440}],
        "outside the week": [
            {"op": "add", "work_date": before_week, "minutes": 5, "task_id": world.task.id}
        ],
        "charge code not shared": [
            {"op": "add", "work_date": day2, "minutes": 5, "charge_code_id": world.code.id}
        ],
        "two changes to one entry": [
            {"op": "update", "entry_id": locked.e1, "minutes": 10},
            {"op": "delete", "entry_id": locked.e1},
        ],
        "read-only leave entry": [{"op": "update", "entry_id": leave.id, "minutes": 10}],
        "update that changes nothing": [{"op": "update", "entry_id": locked.e1}],
        "both targets": [
            {
                "op": "add",
                "work_date": day2,
                "minutes": 5,
                "task_id": world.task.id,
                "charge_code_id": world.code.id,
            }
        ],
        "no changes": [],
    }
    for name, changes in bad.items():
        assert locked.file(changes).status_code == 422, name
    assert locked.file(locked.usual_changes(), reason="").status_code == 422  # a reason is needed
    assert world.client.get("/time/edit-requests", headers=hdr(world.emp)).json() == []


def test_approval_fails_cleanly_if_the_rules_stopped_passing(world: World) -> None:
    locked = Locked(world)
    day = locked.ws + timedelta(days=3)
    change = [{"op": "add", "work_date": day.isoformat(), "minutes": 100, "task_id": world.task.id}]
    assert locked.file(change).status_code == 201
    week = world.session.scalars(
        select(TimesheetWeek).where(TimesheetWeek.user_id == world.emp.id)
    ).one()
    # Meanwhile that day fills up (a long entry appears directly), so 100 more no longer fits.
    world.session.add(
        TimeEntry(
            user_id=world.emp.id,
            week_id=week.id,
            work_date=day,
            minutes=1400,
            task_id=world.task.id,
            source="manual",
        )
    )
    world.session.flush()
    approval_id = locked.approval_id()
    res = world.client.post(f"/approvals/{approval_id}/approve", headers=hdr(world.boss))
    assert res.status_code == 422 and "24 hours" in res.json()["detail"]
    bulk = world.client.post(
        "/approvals/bulk-approve", json={"approval_ids": [approval_id]}, headers=hdr(world.boss)
    ).json()
    assert bulk["approved"] == [] and "24 hours" in bulk["skipped"][0]["reason"]
    assert locked.approval_id() == approval_id  # still waiting in the inbox
    request = world.client.get("/time/edit-requests", headers=hdr(world.emp)).json()[0]
    assert request["status"] == "pending"
    assert [e for e in locked.entries() if e["work_date"] == day.isoformat()][0]["minutes"] == 1400


def test_the_requester_can_cancel_a_pending_request(world: World) -> None:
    locked = Locked(world)
    request_id = locked.file(locked.usual_changes()).json()["id"]
    approval_id = locked.approval_id()
    url = f"/time/edit-requests/{request_id}/cancel"
    assert world.client.post(url, headers=hdr(world.boss)).status_code == 404  # not their request
    res = world.client.post(url, headers=hdr(world.emp))
    assert res.status_code == 200 and res.json()["status"] == "cancelled"
    assert world.client.get("/approvals/inbox", headers=hdr(world.boss)).json() == []
    assert world.client.post(url, headers=hdr(world.emp)).status_code == 409  # already cancelled
    approve = world.client.post(f"/approvals/{approval_id}/approve", headers=hdr(world.boss))
    assert approve.status_code == 409
    steps = world.client.get(f"/approvals/{approval_id}/history", headers=hdr(world.emp)).json()
    assert [s["action"] for s in steps] == ["submitted", "cancelled"]


def test_only_those_involved_can_read_an_edit_request(world: World) -> None:
    locked = Locked(world)
    request_id = locked.file(locked.usual_changes()).json()["id"]
    stranger = User(employee_code="NOSY", name="NOSY", email="nosy@x.io")
    world.session.add(stranger)
    world.session.flush()
    url = f"/time/edit-requests/{request_id}"
    assert world.client.get(url, headers=hdr(world.emp)).status_code == 200
    assert world.client.get(url, headers=hdr(world.boss)).status_code == 200
    assert world.client.get(url, headers=hdr(stranger)).status_code == 404
    missing = world.client.get("/time/edit-requests/999999999", headers=hdr(world.emp))
    assert missing.status_code == 404
