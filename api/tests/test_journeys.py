"""End-to-end journeys (WH-90): whole stories through the API, the way the front end will use it.

The design spec lists browser journeys (Playwright). Those need the front end, and leave, payslips
and the client portal are not built yet, so these four cover what exists today:
  1. log a week, submit it, get it approved
  2. approve one week and send another back with a reason, then fix and resubmit
  3. fix a locked week through an edit request (approved once, sent back once)
  4. the manager is away and nobody acts in time: delegation, then escalation
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from conftest import DAY, World, hdr
from sqlalchemy import select

from workhub_api import jobs
from workhub_api.models import (
    Approval,
    AuditEvent,
    ChargeCodeTeam,
    RoleAssignment,
    Team,
    TeamMember,
    User,
)
from workhub_api.routing import HOUSEKEEPING

TODAY = date.today()


def monday(on: date) -> date:
    return on - timedelta(days=on.weekday())


def entry(w: World, day: date, minutes: int, **target: int) -> dict[str, Any]:
    body = {"work_date": day.isoformat(), "minutes": minutes, **(target or {"task_id": w.task.id})}
    res = w.client.post("/time/entries", json=body, headers=hdr(w.emp))
    assert res.status_code == 201, res.text
    data: dict[str, Any] = res.json()
    return data


def week_of(w: World, on: date) -> dict[str, Any]:
    res = w.client.get("/time/week", params={"on": on.isoformat()}, headers=hdr(w.emp))
    data: dict[str, Any] = res.json()
    return data


def submit_week(w: World, ws: date) -> None:
    res = w.client.post(f"/time/weeks/{ws}/submit", headers=hdr(w.emp))
    assert res.status_code == 200, res.text


def inbox(w: World, who: User) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = w.client.get("/approvals/inbox", headers=hdr(who)).json()
    return rows


def act(w: World, who: User, approval_id: int, action: str, **body: Any) -> int:
    url = f"/approvals/{approval_id}/{action}"
    return int(w.client.post(url, json=body or None, headers=hdr(who)).status_code)


def history(w: World, approval_id: int) -> list[str]:
    steps = w.client.get(f"/approvals/{approval_id}/history", headers=hdr(w.emp)).json()
    return [s["action"] for s in steps]


def manager(w: World, code: str, boss: User | None = None) -> User:
    user = User(
        employee_code=code,
        name=code,
        email=f"{code.lower()}@x.io",
        manager_id=boss.id if boss else None,
    )
    w.session.add(user)
    w.session.flush()
    w.session.add(RoleAssignment(user_id=user.id, role="manager"))
    w.session.flush()
    return user


def test_journey_1_log_submit_and_get_approved(world: World) -> None:
    team = Team(name="Delivery")  # a charge code only works for the teams it is shared with
    world.session.add(team)
    world.session.flush()
    world.session.add_all(
        [
            TeamMember(team_id=team.id, user_id=world.emp.id),
            ChargeCodeTeam(charge_code_id=world.code.id, team_id=team.id),
        ]
    )
    world.session.flush()
    ws = monday(DAY)
    entry(world, ws, 240)
    entry(world, ws + timedelta(days=1), 120, charge_code_id=world.code.id)
    week = week_of(world, ws)
    assert week["status"] == "draft" and sum(week["day_minutes"].values()) == 360

    submit_week(world, ws)
    rows = inbox(world, world.boss)
    assert [(r["requester_name"], r["subject_type"], r["total_minutes"]) for r in rows] == [
        ("Emp", "week", 360)
    ]
    assert inbox(world, world.emp) == []  # your own week is not in your inbox
    approval_id = rows[0]["approval_id"]

    assert act(world, world.boss, approval_id, "approve") == 200
    week = week_of(world, ws)
    assert week["status"] == "approved" and week["locked"] is True
    late = {"work_date": ws.isoformat(), "minutes": 5, "task_id": world.task.id}
    assert world.client.post("/time/entries", json=late, headers=hdr(world.emp)).status_code == 409
    assert inbox(world, world.boss) == []
    assert history(world, approval_id) == ["submitted", "approved"]
    approved = world.session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity == "approval",
            AuditEvent.entity_id == approval_id,
            AuditEvent.action == "approved",
        )
    ).one()
    assert approved.actor_id == world.boss.id  # the audit log says who approved


def test_journey_2_approve_one_week_send_another_back(world: World) -> None:
    ws1, ws2 = monday(DAY), monday(DAY) - timedelta(days=7)
    entry(world, ws1, 480)
    good = entry(world, ws2, 480)
    wrong = entry(world, ws2 + timedelta(days=1), 60)
    submit_week(world, ws1)
    submit_week(world, ws2)
    waiting = {r["week_start"]: r["approval_id"] for r in inbox(world, world.boss)}
    assert set(waiting) == {ws1.isoformat(), ws2.isoformat()}

    assert act(world, world.boss, waiting[ws1.isoformat()], "approve") == 200
    why = "Day 2 is not project work"
    sent = act(
        world,
        world.boss,
        waiting[ws2.isoformat()],
        "send-back",
        reason=why,
        entry_ids=[wrong["id"]],
    )
    assert sent == 200

    second = week_of(world, ws2)
    assert second["status"] == "draft"  # back to the employee
    reasons = {e["id"]: e["sent_back_reason"] for e in second["entries"]}
    assert reasons[wrong["id"]] == why and reasons[good["id"]] is None  # pinned on the right entry
    assert week_of(world, ws1)["status"] == "approved"

    res = world.client.delete(f"/time/entries/{wrong['id']}", headers=hdr(world.emp))
    assert res.status_code == 204
    submit_week(world, ws2)
    again = inbox(world, world.boss)
    assert len(again) == 1 and again[0]["approval_id"] != waiting[ws2.isoformat()]  # a new approval
    assert act(world, world.boss, again[0]["approval_id"], "approve") == 200
    assert all(week_of(world, ws)["status"] == "approved" for ws in (ws1, ws2))
    assert history(world, waiting[ws2.isoformat()]) == ["submitted", "sent_back"]


def test_journey_3_fix_a_locked_week_with_an_edit_request(world: World) -> None:
    ws = monday(DAY)
    e1 = entry(world, ws, 60)
    e2 = entry(world, ws, 30)
    submit_week(world, ws)
    assert act(world, world.boss, inbox(world, world.boss)[0]["approval_id"], "approve") == 200

    def file(changes: list[dict[str, Any]], reason: str) -> Any:
        url = f"/time/weeks/{ws}/edit-requests"
        return world.client.post(
            url, json={"reason": reason, "changes": changes}, headers=hdr(world.emp)
        )

    fix = [
        {"op": "update", "entry_id": e1["id"], "minutes": 120},
        {"op": "delete", "entry_id": e2["id"]},
        {
            "op": "add",
            "work_date": (ws + timedelta(days=2)).isoformat(),
            "minutes": 45,
            "task_id": world.task.id,
        },
    ]
    assert file(fix, "Wrong hours").status_code == 201
    assert act(world, world.boss, inbox(world, world.boss)[0]["approval_id"], "approve") == 200
    week = week_of(world, ws)
    assert sorted(e["minutes"] for e in week["entries"]) == [45, 120]
    assert week["status"] == "approved" and week["locked"] is True  # fixed, and still locked

    again = file([{"op": "update", "entry_id": e1["id"], "minutes": 400}], "Try again")
    assert again.status_code == 201
    sent = act(
        world, world.boss, inbox(world, world.boss)[0]["approval_id"], "send-back", reason="No"
    )
    assert sent == 200
    assert sorted(e["minutes"] for e in week_of(world, ws)["entries"]) == [45, 120]  # untouched
    mine = world.client.get("/time/edit-requests", headers=hdr(world.emp)).json()
    assert [r["status"] for r in mine] == ["rejected", "approved"]  # newest first

    by_boss = set(
        world.session.scalars(
            select(AuditEvent.action).where(
                AuditEvent.entity == "time_entry", AuditEvent.actor_id == world.boss.id
            )
        )
    )
    assert by_boss == {"created", "updated", "deleted"}  # the approved changes are on the approver


def test_journey_4_manager_away_and_nobody_acts_in_time(world: World) -> None:
    top = manager(world, "TOP")
    deputy = manager(world, "DEP", top)
    away = {
        "to_user_id": deputy.id,
        "starts_on": TODAY.isoformat(),
        "ends_on": (TODAY + timedelta(days=3)).isoformat(),
    }
    assert world.client.post("/delegations", json=away, headers=hdr(world.boss)).status_code == 201

    ws = monday(DAY)
    entry(world, ws, 300)
    submit_week(world, ws)
    assert inbox(world, world.boss) == []  # went straight to the deputy
    waiting = inbox(world, deputy)
    assert len(waiting) == 1
    approval_id = waiting[0]["approval_id"]

    approval = world.session.get(Approval, approval_id)
    assert approval is not None
    approval.due_at = datetime.now(UTC) - timedelta(hours=1)  # the deadline passes
    world.session.flush()
    jobs.enqueue(world.session, HOUSEKEEPING)
    world.session.flush()
    assert jobs.run_one(world.session, kinds={HOUSEKEEPING}) is True  # what the worker does

    world.session.refresh(approval)
    assert approval.approver_id == top.id and approval.level == 2
    assert inbox(world, deputy) == [] and len(inbox(world, top)) == 1
    assert act(world, deputy, approval_id, "approve") == 404  # no longer theirs
    assert act(world, top, approval_id, "approve") == 200
    assert history(world, approval_id) == ["submitted", "escalated", "approved"]
    assert week_of(world, ws)["status"] == "approved"
