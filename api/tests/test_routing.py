from datetime import UTC, date, datetime, time, timedelta

from conftest import World, add, hdr, submit, week_json
from sqlalchemy import select

from workhub_api import jobs
from workhub_api.models import Approval, Holiday, Job, Location, RoleAssignment, User
from workhub_api.routing import (
    HOUSEKEEPING,
    IST,
    add_working_days,
    apply_delegations,
    escalate_overdue,
    week_due_at,
    work_weekdays,
)

TODAY = date.today()


def person(w: World, code: str, manager: User | None = None) -> User:
    user = User(
        employee_code=code,
        name=code,
        email=f"{code.lower()}@x.io",
        manager_id=manager.id if manager else None,
    )
    w.session.add(user)
    w.session.flush()
    w.session.add(RoleAssignment(user_id=user.id, role="manager"))  # people made here can approve
    w.session.flush()
    return user


def delegate(w: World, frm: User, to: User, start: date = TODAY, days: int = 7) -> int:
    body = {
        "to_user_id": to.id,
        "starts_on": start.isoformat(),
        "ends_on": (start + timedelta(days=days)).isoformat(),
    }
    status: int = w.client.post("/delegations", json=body, headers=hdr(frm)).status_code
    return status


def my_approval(w: World) -> Approval:
    return w.session.scalars(select(Approval).where(Approval.requester_id == w.emp.id)).one()


def history(w: World, approval_id: int) -> list[str]:
    steps = w.client.get(f"/approvals/{approval_id}/history", headers=hdr(w.emp)).json()
    return [s["action"] for s in steps]


def test_new_approval_goes_to_the_delegate_and_gets_a_due_date(world: World) -> None:
    deputy = person(world, "D1")
    assert delegate(world, world.boss, deputy) == 201
    add(world)
    start = str(week_json(world)["week_start"])
    assert (
        world.client.post(f"/time/weeks/{start}/submit", headers=hdr(world.emp)).status_code == 200
    )
    inbox = world.client.get("/approvals/inbox", headers=hdr(deputy)).json()
    assert [i["requester_name"] for i in inbox] == ["Emp"]
    assert world.client.get("/approvals/inbox", headers=hdr(world.boss)).json() == []
    approval = my_approval(world)
    assert approval.due_at is not None and approval.due_at > datetime.now(UTC) + timedelta(days=1)
    url = f"/approvals/{approval.id}/approve"
    assert world.client.post(url, headers=hdr(deputy)).status_code == 200  # the delegate can act


def test_a_delegation_created_later_moves_pending_approvals(world: World) -> None:
    add(world)
    approval_id = submit(world)  # waiting with the boss
    deputy = person(world, "D2")
    assert delegate(world, world.boss, deputy) == 201
    assert history(world, approval_id) == ["submitted", "delegated"]
    url = f"/approvals/{approval_id}/approve"
    assert world.client.post(url, headers=hdr(world.boss)).status_code == 404  # no longer theirs
    assert world.client.post(url, headers=hdr(deputy)).status_code == 200


def test_a_future_delegation_does_not_move_anything_yet(world: World) -> None:
    add(world)
    submit(world)
    assert delegate(world, world.boss, person(world, "D3"), start=TODAY + timedelta(days=3)) == 201
    assert len(world.client.get("/approvals/inbox", headers=hdr(world.boss)).json()) == 1


def test_two_way_delegation_does_not_ping_pong(world: World) -> None:
    deputy = person(world, "D4")
    assert delegate(world, world.boss, deputy) == 201
    assert delegate(world, deputy, world.boss) == 201
    add(world)
    start = str(week_json(world)["week_start"])
    world.client.post(f"/time/weeks/{start}/submit", headers=hdr(world.emp))
    approval = my_approval(world)
    for _ in range(3):
        apply_delegations(world.session)
    assert history(world, approval.id).count("delegated") == 1


def test_delegation_rules_and_ownership(world: World) -> None:
    deputy = person(world, "D5")

    def post(body: dict[str, object]) -> int:
        status: int = world.client.post(
            "/delegations", json=body, headers=hdr(world.boss)
        ).status_code
        return status

    ok = {"to_user_id": deputy.id, "starts_on": TODAY.isoformat(), "ends_on": TODAY.isoformat()}
    assert post({**ok, "to_user_id": world.boss.id}) == 422  # to yourself
    assert post({**ok, "to_user_id": 999999999}) == 422  # unknown person
    assert post({**ok, "ends_on": (TODAY - timedelta(days=1)).isoformat()}) == 422  # before start
    past = (TODAY - timedelta(days=5)).isoformat()
    assert post({**ok, "starts_on": past, "ends_on": past}) == 422  # already over
    assert post(ok) == 201
    mine = world.client.get("/delegations", headers=hdr(world.boss)).json()
    assert [d["to_user_id"] for d in mine] == [deputy.id]
    assert len(world.client.get("/delegations", headers=hdr(deputy)).json()) == 1  # received
    url = f"/delegations/{mine[0]['id']}"
    assert world.client.delete(url, headers=hdr(deputy)).status_code == 404  # not theirs to remove
    assert world.client.delete(url, headers=hdr(world.boss)).status_code == 204
    assert world.client.get("/delegations", headers=hdr(world.boss)).json() == []


def test_overdue_approval_escalates_to_the_managers_manager(world: World) -> None:
    top = person(world, "TOP")
    world.boss.manager_id = top.id
    add(world)
    approval_id = submit(world)
    approval = my_approval(world)
    approval.due_at = datetime.now(UTC) - timedelta(hours=1)
    world.session.flush()
    escalate_overdue(world.session)
    world.session.refresh(approval)
    assert approval.approver_id == top.id and approval.level == 2
    assert approval.due_at is not None and approval.due_at > datetime.now(UTC)  # a fresh due date
    assert history(world, approval_id) == ["submitted", "escalated"]
    assert len(world.client.get("/approvals/inbox", headers=hdr(top)).json()) == 1
    escalate_overdue(world.session)  # not overdue any more, so it stays put
    world.session.refresh(approval)
    assert approval.approver_id == top.id and approval.level == 2


def test_overdue_with_nobody_above_stays_put(world: World) -> None:
    add(world)
    submit(world)  # the boss has no manager
    approval = my_approval(world)
    approval.due_at = datetime.now(UTC) - timedelta(hours=1)
    world.session.flush()
    escalate_overdue(world.session)
    world.session.refresh(approval)
    assert approval.approver_id == world.boss.id and approval.level == 1


def test_working_days_skip_weekends_holidays_and_follow_the_work_week(world: World) -> None:
    friday = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)
    s = world.session
    assert add_working_days(s, friday, 0, None) == friday
    assert add_working_days(s, friday, 2, None).date() == date(2026, 11, 17)  # Tuesday
    assert add_working_days(s, friday, 2, None, "Mon-Sat").date() == date(2026, 11, 16)  # Monday
    place = Location(name="Test place")
    s.add(place)
    s.flush()
    s.add(Holiday(location_id=place.id, on_date=date(2026, 11, 16), name="Monday off"))
    s.flush()
    assert add_working_days(s, friday, 2, place.id).date() == date(
        2026, 11, 18
    )  # skips the holiday
    assert work_weekdays("Mon-Fri") == {0, 1, 2, 3, 4}
    assert work_weekdays("Mon,Wed") == {0, 2}
    assert work_weekdays("nonsense") == {0, 1, 2, 3, 4}


def test_housekeeping_job_runs_and_schedules_itself_again(world: World) -> None:
    s = world.session
    assert HOUSEKEEPING in jobs.HANDLERS
    first = jobs.enqueue(s, HOUSEKEEPING)
    s.flush()
    assert jobs.run_one(s, kinds={HOUSEKEEPING}) is True
    assert first.status == "done"
    soon = datetime.now(UTC) + timedelta(minutes=14)
    waiting = s.scalars(select(Job).where(Job.kind == HOUSEKEEPING, Job.status == "queued")).all()
    assert any(j.id != first.id and j.run_at > soon for j in waiting)  # next run in ~15 minutes


def test_a_week_is_due_monday_6pm_ist_after_it_ends_and_late_ones_keep_the_old_rule(
    world: World,
) -> None:
    s = world.session
    week = date(2026, 11, 2)  # a Monday
    monday_6pm = datetime(2026, 11, 9, 12, 30, tzinfo=UTC)  # 18:00 IST
    early = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)
    assert week_due_at(s, world.emp, week, now=early) == monday_6pm
    on_the_day = datetime(2026, 11, 9, 12, 29, tzinfo=UTC)  # a minute before the deadline
    assert week_due_at(s, world.emp, week, now=on_the_day) == monday_6pm
    late = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)  # after the deadline: 2 working days from now
    assert week_due_at(s, world.emp, week, now=late) == datetime(2026, 11, 12, 9, 0, tzinfo=UTC)

    place = Location(name="Monday-off place")  # that Monday is a holiday, so the next day
    s.add(place)
    s.flush()
    s.add(Holiday(location_id=place.id, on_date=date(2026, 11, 9), name="Holiday"))
    world.emp.location_id = place.id
    s.flush()
    assert week_due_at(s, world.emp, week, now=early) == datetime(2026, 11, 10, 12, 30, tzinfo=UTC)


def test_submitting_this_week_sets_the_monday_deadline(world: World) -> None:
    start = TODAY - timedelta(days=TODAY.weekday())
    assert add(world, 60, day=TODAY) == 201
    res = world.client.post(f"/time/weeks/{start}/submit", headers=hdr(world.emp))
    assert res.status_code == 200
    expected = datetime.combine(start + timedelta(days=7), time(18, 0), tzinfo=IST)
    assert my_approval(world).due_at == expected
