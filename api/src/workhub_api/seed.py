"""Sample data for development (first slice of WH-90): the three of us, 2 locations, 3 teams.

Run:  uv run python -m workhub_api.seed
Safe to run twice: it does nothing if the sample users already exist. Emails are made up
(@example.com). Use a person's id as the X-User-Id header (needs DEV_AUTH=true).

Chain: Jim -> Jana -> Jay. Jim's week goes to Jana to approve; Jana's goes to Jay.
Jay is the top of the chain, so Jay has no manager and can't submit a week.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from workhub_api.models import (
    ChargeCode,
    ChargeCodeTeam,
    Client,
    Holiday,
    Location,
    OrgSettings,
    Project,
    ProjectMember,
    ProjectTeam,
    RoleAssignment,
    Task,
    TaskList,
    TaskStatus,
    Team,
    TeamMember,
    User,
    WorkOrder,
)

# (name, location index, team name, manager name, extra roles). Everyone is also an employee.
PEOPLE = [
    ("Jay", 1, "Frontend", None, ["manager", "admin"]),
    ("Jana", 0, "Platform", "Jay", ["manager", "hr"]),
    ("Jim", 0, "Core Engine", "Jana", ["finance"]),
]
HOLIDAYS = [(date(2026, 12, 25), "Christmas"), (date(2027, 1, 26), "Republic Day")]
TASKS = ["WH-01 Backend repo and CI", "WH-03 Core database schema", "WH-20 Time API"]


def seed(session: Session) -> bool:
    """Add the sample data. Returns False (and adds nothing) if it is already there."""
    if session.scalar(select(User.id).where(User.employee_code == "AMP001")):
        return False

    session.add(OrgSettings())
    locations = [Location(name="Chennai"), Location(name="Bengaluru")]
    teams = {name: Team(name=name) for _, _, name, _, _ in PEOPLE}
    session.add_all([*locations, *teams.values()])
    session.flush()
    session.add_all(
        Holiday(location_id=loc.id, on_date=d, name=name)
        for loc in locations
        for d, name in HOLIDAYS
    )

    users: dict[str, User] = {}
    for i, (name, loc, team, manager, roles) in enumerate(PEOPLE):
        user = User(
            employee_code=f"AMP{i + 1:03d}",
            name=name,
            email=f"{name.lower()}@example.com",
            location_id=locations[loc].id,
            manager_id=users[manager].id if manager else None,  # managers come earlier in PEOPLE
            joined_on=date(2026, 11, 13),
        )
        session.add(user)
        session.flush()
        users[name] = user
        session.add_all(RoleAssignment(user_id=user.id, role=r) for r in ["employee", *roles])
        session.add(TeamMember(team_id=teams[team].id, user_id=user.id))

    codes = [ChargeCode(code=c, name=c) for c in ("Bench", "Training", "Proposal")]
    client = Client(name="Ampera (internal)")
    session.add_all([*codes, client])
    session.flush()
    session.add_all(
        ChargeCodeTeam(charge_code_id=c.id, team_id=t.id) for c in codes for t in teams.values()
    )
    order = WorkOrder(client_id=client.id, code="SOW-11101", starts_on=date(2026, 11, 13))
    session.add(order)
    session.flush()

    project = Project(
        key="ATPL-106", name="WorkHub build", manager_id=users["Jim"].id, work_order_id=order.id
    )
    session.add(project)
    session.flush()
    statuses = [
        TaskStatus(project_id=project.id, name=s, position=p, is_closed=(s == "Done"))
        for p, s in enumerate(["Open", "In progress", "Done"])
    ]
    backlog = TaskList(project_id=project.id, name="Backlog")
    session.add_all([*statuses, backlog])
    session.flush()
    session.add_all(
        Task(task_list_id=backlog.id, status_id=statuses[0].id, key=f"ATPL-106-T{n}", title=title)
        for n, title in enumerate(TASKS, start=1)
    )
    session.add_all(ProjectTeam(project_id=project.id, team_id=t.id) for t in teams.values())
    session.add_all(ProjectMember(project_id=project.id, user_id=u.id) for u in users.values())
    session.flush()
    return True


if __name__ == "__main__":
    from workhub_api.db import engine

    with Session(engine) as s:
        if seed(s):
            s.commit()
            print("Seeded. Use these ids as X-User-Id (DEV_AUTH=true):")
            for u in s.scalars(select(User).order_by(User.id)):
                print(f"  {u.id:>3}  {u.employee_code}  {u.name:<6} manager_id={u.manager_id}")
        else:
            print("Sample data is already there; nothing changed.")
