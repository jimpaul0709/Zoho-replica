"""Synthetic data for testing on the shared dev database: 24 made-up people (SYN001 to SYN024).

Run (API must be running; people are inserted directly, everything else goes through the API so the
real rules, approvals and audit trail are exercised):

    uv run python -m workhub_api.seed_synthetic --api http://localhost:8000

What you get: 3 managers and 21 employees, three finished weeks of time (the older ones approved,
the latest one waiting for approval, one day sent back), the current week part-filled, leave
balances, some leave requests (pending, approved, withdrawn) and last month's payslips, published.
Safe to run twice: it stops once the SYN people have time logged. Remove them by employee code.
"""

import argparse
import io
import random
import zipfile
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from workhub_api.models import Location, RoleAssignment, Team, TeamMember, TimeEntry, User
from workhub_api.seed import DEV_PASSWORD, ensure_passwords

FIRST = (
    "Asha Ben Chitra Dev Esha Farid Gita Hari Isha Jai Kavya Lena "
    "Manu Nila Omar Priya Quin Ravi Sana Tara Uma Vik Wren Zoya"
).split()
LAST = "Rao Iyer Nair Das Shah Khan Menon Bose Pillai Reddy Joshi Kapoor".split()
COUNT = 24
MANAGERS = 3  # SYN001..SYN003 report to Jana and Jay; everyone else reports to them
MANAGER_EMAILS = [f"syn{i:03d}@example.com" for i in range(1, MANAGERS + 1)]
errors: list[str] = []


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def create_people(session: Session) -> list[User]:
    have = session.scalars(
        select(User).where(User.employee_code.like("SYN%")).order_by(User.id)
    ).all()
    if have:  # an earlier run stopped half way: reuse the people, but never log time twice
        if session.scalar(select(TimeEntry.id).where(TimeEntry.user_id.in_([u.id for u in have]))):
            raise SystemExit("SYN people already have time; nothing to do.")
        return list(have)
    boss = {n: session.scalar(select(User).where(User.name == n)) for n in ("Jana", "Jay")}
    if not all(boss.values()):
        raise SystemExit("Run `python -m workhub_api.seed` first (Jana and Jay are missing).")
    locations = session.scalars(select(Location).order_by(Location.id)).all()
    teams = session.scalars(select(Team).order_by(Team.id)).all()
    people: list[User] = []
    for i in range(COUNT):
        manager = (boss["Jana"], boss["Jay"], boss["Jana"])[i] if i < MANAGERS else people[i % 3]
        assert manager is not None
        user = User(
            employee_code=f"SYN{i + 1:03d}",
            name=f"{FIRST[i]} {LAST[i % len(LAST)]}",
            email=f"syn{i + 1:03d}@example.com",
            location_id=locations[i % len(locations)].id,
            manager_id=manager.id,
            joined_on=date(2026, 1, 5),
        )
        session.add(user)
        session.flush()
        roles = ["employee", "manager"] if i < MANAGERS else ["employee"]
        session.add_all(RoleAssignment(user_id=user.id, role=r) for r in roles)
        session.add(TeamMember(team_id=teams[i % len(teams)].id, user_id=user.id))
        people.append(user)
    ensure_passwords(session)
    session.commit()
    return people


@contextmanager
def client(base: str, email: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=base, timeout=120) as c:
        res = c.post("/auth/login", json={"email": email, "password": DEV_PASSWORD})
        res.raise_for_status()
        c.headers["Authorization"] = "Bearer " + res.json()["token"]
        yield c


def call(c: httpx.Client, method: str, path: str, **kw: Any) -> Any:
    """The JSON answer, or None (and a note in `errors`) if the API said no."""
    res = c.request(method, path, **kw)
    if res.status_code >= 400:
        errors.append(f"{method} {path} -> {res.status_code} {res.text[:120]}")
        return None
    return res.json() if res.content else {}


def log_time(base: str, n: int, email: str, weeks: list[date], today: date) -> None:
    """Fill Monday to Friday (up to today) in every week, then submit the finished weeks."""
    rng = random.Random(n)
    with client(base, email) as c:
        targets = call(c, "GET", "/time/targets")
        if not targets:
            return
        tasks = [t["id"] for t in targets["tasks"]]
        codes = {x["code"]: x["id"] for x in targets["charge_codes"]}
        bench = codes.get("Bench") or next(iter(codes.values()))
        other = codes.get("Training") or bench
        for ws in weeks:
            for d in range(5):
                day = ws + timedelta(days=d)
                if day > today:
                    break
                roll = rng.random()
                if roll < 0.60 and tasks:
                    parts = [("task_id", rng.choice(tasks), 480)]
                elif roll < 0.85 and tasks:
                    parts = [("task_id", rng.choice(tasks), 300), ("charge_code_id", other, 180)]
                elif roll < 0.95 and tasks:
                    parts = [("task_id", rng.choice(tasks), 360)]  # a short day
                else:
                    parts = [("charge_code_id", bench, 480)]
                for key, target, minutes in parts:
                    body = {"work_date": day.isoformat(), "minutes": minutes, key: target}
                    call(c, "POST", "/time/entries", json=body)
        for ws in weeks[:-1]:  # the current week stays a draft
            if n % 11 == 10 and ws == weeks[-2]:
                continue  # a couple of people are late with their last week
            call(c, "POST", f"/time/weeks/{ws}/submit")


def approve_old_weeks(base: str, email: str, cutoff: date, syn_ids: set[int]) -> None:
    with client(base, email) as c:
        items = call(c, "GET", "/approvals/inbox") or []
        old = [
            i["approval_id"]
            for i in items
            if i["subject_type"] == "week"
            and i["requester_id"] in syn_ids
            and i["week_start"] < cutoff.isoformat()
        ]
        if old:
            call(c, "POST", "/approvals/bulk-approve", json={"approval_ids": old})


def leave_flow(base: str, people: list[User], today: date) -> None:
    with client(base, "jana@example.com") as hr:
        types = {t["name"]: t["id"] for t in call(hr, "GET", "/leave/types") or []}
        for u in people:
            for name, hours in (("Earned", 120), ("Casual", 40)):
                if name in types:
                    body = {
                        "user_id": u.id,
                        "leave_type_id": types[name],
                        "leave_year": today.year,
                        "opening": hours,
                    }
                    call(hr, "PUT", "/leave/balances", json=body)
    if "Casual" not in types:
        return
    next_mon = monday(today) + timedelta(days=7)
    for n, u in enumerate(people):
        if n % 3:
            continue
        day = (next_mon + timedelta(days=n % 5)).isoformat()
        with client(base, u.email) as c:
            body = {
                "leave_type_id": types["Casual"],
                "from_date": day,
                "to_date": day,
                "reason": "Synthetic test leave",
            }
            made = call(c, "POST", "/leave/requests", json=body)
            if made and n % 9 == 0:
                call(c, "POST", f"/leave/requests/{made['id']}/withdraw")
    for email in MANAGER_EMAILS:  # each manager approves every other leave request waiting
        with client(base, email) as c:
            items = call(c, "GET", "/approvals/inbox") or []
            for k, i in enumerate(x for x in items if x["subject_type"] == "leave"):
                if k % 2 == 0:
                    call(c, "POST", f"/approvals/{i['approval_id']}/approve")


def payslips(base: str, people: list[User], today: date) -> None:
    month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for u in people:
            text = f"%PDF-1.4\nSynthetic payslip {u.employee_code} {month}\n%%EOF\n"
            z.writestr(f"{u.employee_code}_{month}.pdf", text)
    with client(base, "jana@example.com") as hr:
        files = [("files", (f"{month}.zip", buf.getvalue(), "application/zip"))]
        made = call(hr, "POST", "/payslips/batches", data={"month": month}, files=files)
        if made:
            call(hr, "POST", f"/payslips/batches/{made['id']}/publish")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    base = ap.parse_args().api
    from workhub_api.db import engine

    today = date.today()
    this_mon = monday(today)
    weeks = [this_mon - timedelta(days=7 * k) for k in (3, 2, 1, 0)]
    with Session(engine) as s:
        people = create_people(s)
        for u in people:
            s.refresh(u)  # commit expired them; load again before they leave the session
        s.expunge_all()
    syn_ids = {u.id for u in people}
    print(f"created {len(people)} people; logging time (a few minutes)...")
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda p: log_time(base, p[0], p[1].email, weeks, today), enumerate(people)))
    print("approving older weeks...")
    cutoff = this_mon - timedelta(days=7)  # last week stays pending
    for email in [*MANAGER_EMAILS, "jana@example.com", "jay@example.com"]:
        approve_old_weeks(base, email, cutoff, syn_ids)
    with client(base, MANAGER_EMAILS[0]) as c:  # send one day of one report's latest week back
        items = call(c, "GET", "/approvals/inbox") or []
        waiting = [i for i in items if i["subject_type"] == "week" and i["requester_id"] in syn_ids]
        if waiting:
            path = (
                f"/approvals/{waiting[0]['approval_id']}/days/{waiting[0]['week_start']}/send-back"
            )
            call(c, "POST", path, json={"reason": "Synthetic test: please add notes for this day"})
    print("leave...")
    leave_flow(base, people, today)
    print("payslips...")
    payslips(base, people, today)
    print(f"done, {len(errors)} call(s) failed")
    for e in errors[:25]:
        print(" ", e)


if __name__ == "__main__":
    main()
