"""Org admin (HR and admin): locations, holidays, teams, charge codes, projects and their tasks.

Lists of people, teams and shared charge codes are replaced as a whole (PUT), so what you send is
what you get. Every create and change is audited. Who can see a project or task is still decided
by visibility.py; this module only sets up the data it reads.
"""

from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from workhub_api.audit import record, snapshot
from workhub_api.db import CurrentUser, SessionDep
from workhub_api.models import (
    ChargeCode,
    ChargeCodeTeam,
    Holiday,
    Location,
    Project,
    ProjectMember,
    ProjectTeam,
    Task,
    TaskList,
    TaskStatus,
    Team,
    TeamMember,
    User,
)
from workhub_api.permissions import roles_of
from workhub_api.users_admin import Staff

router = APIRouter(tags=["org"])

DEFAULT_STATUSES = ["Open", "In progress", "Done"]


# ---------- shared helpers ----------


def _audit(
    session: Session,
    actor: User,
    entity: str,
    row: Any,
    action: str,
    before: dict[str, Any] | None = None,
) -> None:
    record(
        session,
        actor_id=actor.id,
        entity=entity,
        entity_id=row.id,
        action=action,
        before=before,
        after=snapshot(row),
    )


def _require_all(session: Session, model: Any, ids: list[int], what: str) -> None:
    wanted = set(ids)
    found = session.scalar(select(func.count()).select_from(model).where(model.id.in_(wanted)))
    if wanted and found != len(wanted):
        raise HTTPException(422, f"Unknown {what} in the list")


def _set_links(
    session: Session, model: Any, fixed_col: Any, fixed_id: int, other_col: Any, ids: list[int]
) -> None:
    """Make the rows linking `fixed_id` to `other_col` exactly match `ids`."""
    keep = set(ids)
    session.execute(delete(model).where(fixed_col == fixed_id, other_col.not_in(keep)))
    have = set(session.scalars(select(other_col).where(fixed_col == fixed_id)))
    session.add_all(model(**{fixed_col.key: fixed_id, other_col.key: i}) for i in keep - have)
    session.flush()


def _ids(session: Session, link_col: Any, owner_col: Any, owner_id: int) -> list[int]:
    return sorted(session.scalars(select(link_col).where(owner_col == owner_id)))


def _taken(session: Session, column: Any, value: str) -> bool:
    return session.scalar(select(column).where(func.lower(column) == value.lower())) is not None


def _get(session: Session, model: Any, row_id: int, what: str) -> Any:
    row = session.get(model, row_id)
    if row is None:
        raise HTTPException(404, f"No such {what}")
    return row


def _check_manager(session: Session, manager_id: int | None) -> None:
    if manager_id is None:
        return
    manager = session.get(User, manager_id)
    if manager is None or not manager.active:
        raise HTTPException(422, "Manager must be an existing, active user")


# ---------- locations and holidays ----------


class NameIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class LocationOut(BaseModel):
    id: int
    name: str


class HolidayIn(BaseModel):
    location_id: int
    on_date: date
    name: str = Field(min_length=1, max_length=100)


class HolidayOut(HolidayIn):
    id: int


@router.post("/admin/locations", status_code=201)
def create_location(body: NameIn, session: SessionDep, actor: Staff) -> LocationOut:
    if _taken(session, Location.name, body.name):
        raise HTTPException(409, "A location with that name exists")
    loc = Location(name=body.name)
    session.add(loc)
    session.flush()
    _audit(session, actor, "location", loc, "create")
    session.commit()
    return LocationOut(id=loc.id, name=loc.name)


@router.get("/admin/locations")
def list_locations(session: SessionDep, _actor: Staff) -> list[LocationOut]:
    rows = session.scalars(select(Location).order_by(Location.name))
    return [LocationOut(id=r.id, name=r.name) for r in rows]


@router.post("/admin/holidays", status_code=201)
def create_holiday(body: HolidayIn, session: SessionDep, actor: Staff) -> HolidayOut:
    _require_all(session, Location, [body.location_id], "location")
    clash = session.scalar(
        select(Holiday.id).where(
            Holiday.location_id == body.location_id, Holiday.on_date == body.on_date
        )
    )
    if clash is not None:
        raise HTTPException(409, "That location already has a holiday on that date")
    day = Holiday(**body.model_dump())
    session.add(day)
    session.flush()
    _audit(session, actor, "holiday", day, "create")
    session.commit()
    return HolidayOut(id=day.id, **body.model_dump())


@router.get("/admin/holidays")
def list_holidays(
    session: SessionDep, _actor: Staff, location_id: Annotated[int | None, Query()] = None
) -> list[HolidayOut]:
    q = select(Holiday).order_by(Holiday.on_date)
    if location_id is not None:
        q = q.where(Holiday.location_id == location_id)
    return [
        HolidayOut(id=h.id, location_id=h.location_id, on_date=h.on_date, name=h.name)
        for h in session.scalars(q)
    ]


@router.delete("/admin/holidays/{holiday_id}", status_code=204)
def delete_holiday(holiday_id: int, session: SessionDep, actor: Staff) -> Response:
    day = _get(session, Holiday, holiday_id, "holiday")
    _audit(session, actor, "holiday", day, "delete", before=snapshot(day))
    session.delete(day)
    session.commit()
    return Response(status_code=204)


# ---------- teams ----------


class TeamOut(BaseModel):
    id: int
    name: str
    user_ids: list[int]


class UserIds(BaseModel):
    user_ids: list[int]


def _team_out(session: Session, team: Team) -> TeamOut:
    ids = _ids(session, TeamMember.user_id, TeamMember.team_id, team.id)
    return TeamOut(id=team.id, name=team.name, user_ids=ids)


@router.post("/admin/teams", status_code=201)
def create_team(body: NameIn, session: SessionDep, actor: Staff) -> TeamOut:
    if _taken(session, Team.name, body.name):
        raise HTTPException(409, "A team with that name exists")
    team = Team(name=body.name)
    session.add(team)
    session.flush()
    _audit(session, actor, "team", team, "create")
    session.commit()
    return _team_out(session, team)


@router.get("/admin/teams")
def list_teams(session: SessionDep, _actor: Staff) -> list[TeamOut]:
    members: dict[int, list[int]] = {}
    for team_id, user_id in session.execute(select(TeamMember.team_id, TeamMember.user_id)):
        members.setdefault(team_id, []).append(user_id)
    teams = session.scalars(select(Team).order_by(Team.name))
    return [TeamOut(id=t.id, name=t.name, user_ids=sorted(members.get(t.id, []))) for t in teams]


@router.put("/admin/teams/{team_id}/members")
def set_team_members(team_id: int, body: UserIds, session: SessionDep, actor: Staff) -> TeamOut:
    team = _get(session, Team, team_id, "team")
    _require_all(session, User, body.user_ids, "user")
    before = {"user_ids": _ids(session, TeamMember.user_id, TeamMember.team_id, team.id)}
    _set_links(session, TeamMember, TeamMember.team_id, team.id, TeamMember.user_id, body.user_ids)
    record(
        session,
        actor_id=actor.id,
        entity="team",
        entity_id=team.id,
        action="update",
        before=before,
        after={"user_ids": sorted(set(body.user_ids))},
    )
    session.commit()
    return _team_out(session, team)


# ---------- charge codes ----------


class ChargeCodeIn(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    team_ids: list[int] = Field(default_factory=list)


class ChargeCodePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    active: bool | None = None


class TeamIds(BaseModel):
    team_ids: list[int]


class ChargeCodeOut(BaseModel):
    id: int
    code: str
    name: str
    active: bool
    team_ids: list[int]


def _code_out(session: Session, code: ChargeCode) -> ChargeCodeOut:
    teams = _ids(session, ChargeCodeTeam.team_id, ChargeCodeTeam.charge_code_id, code.id)
    return ChargeCodeOut(
        id=code.id, code=code.code, name=code.name, active=code.active, team_ids=teams
    )


def _code_teams(session: Session, code: ChargeCode, team_ids: list[int]) -> None:
    _set_links(
        session,
        ChargeCodeTeam,
        ChargeCodeTeam.charge_code_id,
        code.id,
        ChargeCodeTeam.team_id,
        team_ids,
    )


@router.post("/admin/charge-codes", status_code=201)
def create_charge_code(body: ChargeCodeIn, session: SessionDep, actor: Staff) -> ChargeCodeOut:
    if _taken(session, ChargeCode.code, body.code):
        raise HTTPException(409, "A charge code with that code exists")
    _require_all(session, Team, body.team_ids, "team")
    code = ChargeCode(code=body.code, name=body.name)
    session.add(code)
    session.flush()
    _code_teams(session, code, body.team_ids)
    _audit(session, actor, "charge_code", code, "create")
    session.commit()
    return _code_out(session, code)


@router.get("/admin/charge-codes")
def list_charge_codes(session: SessionDep, _actor: Staff) -> list[ChargeCodeOut]:
    teams: dict[int, list[int]] = {}
    for code_id, team_id in session.execute(
        select(ChargeCodeTeam.charge_code_id, ChargeCodeTeam.team_id)
    ):
        teams.setdefault(code_id, []).append(team_id)
    codes = session.scalars(select(ChargeCode).order_by(ChargeCode.code))
    return [
        ChargeCodeOut(
            id=c.id, code=c.code, name=c.name, active=c.active, team_ids=sorted(teams.get(c.id, []))
        )
        for c in codes
    ]


@router.patch("/admin/charge-codes/{code_id}")
def edit_charge_code(
    code_id: int, body: ChargeCodePatch, session: SessionDep, actor: Staff
) -> ChargeCodeOut:
    code = _get(session, ChargeCode, code_id, "charge code")
    before = snapshot(code)
    for field in body.model_fields_set:
        if getattr(body, field) is not None:
            setattr(code, field, getattr(body, field))
    _audit(session, actor, "charge_code", code, "update", before=before)
    session.commit()
    return _code_out(session, code)


@router.put("/admin/charge-codes/{code_id}/teams")
def set_charge_code_teams(
    code_id: int, body: TeamIds, session: SessionDep, actor: Staff
) -> ChargeCodeOut:
    code = _get(session, ChargeCode, code_id, "charge code")
    _require_all(session, Team, body.team_ids, "team")
    before = {
        "team_ids": _ids(session, ChargeCodeTeam.team_id, ChargeCodeTeam.charge_code_id, code.id)
    }
    _code_teams(session, code, body.team_ids)
    record(
        session,
        actor_id=actor.id,
        entity="charge_code",
        entity_id=code.id,
        action="update",
        before=before,
        after={"team_ids": sorted(set(body.team_ids))},
    )
    session.commit()
    return _code_out(session, code)


# ---------- projects and tasks ----------


class ProjectIn(BaseModel):
    key: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=200)
    group_name: str | None = None
    manager_id: int | None = None
    visibility: Literal["public", "private"] = "public"


class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    group_name: str | None = None
    status: str | None = Field(default=None, min_length=1, max_length=30)
    manager_id: int | None = None
    visibility: Literal["public", "private"] | None = None


class ProjectOut(BaseModel):
    id: int
    key: str
    name: str
    group_name: str | None
    status: str
    visibility: str
    manager_id: int | None
    member_ids: list[int]
    team_ids: list[int]


def _to_project_out(p: Project, member_ids: list[int], team_ids: list[int]) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        key=p.key,
        name=p.name,
        group_name=p.group_name,
        status=p.status,
        visibility=p.visibility,
        manager_id=p.manager_id,
        member_ids=sorted(member_ids),
        team_ids=sorted(team_ids),
    )


def _project_out(session: Session, p: Project) -> ProjectOut:
    return _to_project_out(
        p,
        _ids(session, ProjectMember.user_id, ProjectMember.project_id, p.id),
        _ids(session, ProjectTeam.team_id, ProjectTeam.project_id, p.id),
    )


@router.post("/admin/projects", status_code=201)
def create_project(body: ProjectIn, session: SessionDep, actor: Staff) -> ProjectOut:
    if _taken(session, Project.key, body.key):
        raise HTTPException(409, "A project with that key exists")
    _check_manager(session, body.manager_id)
    project = Project(**body.model_dump())
    session.add(project)
    session.flush()
    session.add(TaskList(project_id=project.id, name="Backlog"))
    session.add_all(
        TaskStatus(project_id=project.id, name=n, position=i, is_closed=(n == "Done"))
        for i, n in enumerate(DEFAULT_STATUSES)
    )
    _audit(session, actor, "project", project, "create")
    session.commit()
    return _project_out(session, project)


@router.get("/admin/projects")
def list_projects(session: SessionDep, _actor: Staff) -> list[ProjectOut]:
    members: dict[int, list[int]] = {}
    for project_id, user_id in session.execute(
        select(ProjectMember.project_id, ProjectMember.user_id)
    ):
        members.setdefault(project_id, []).append(user_id)
    teams: dict[int, list[int]] = {}
    for project_id, team_id in session.execute(select(ProjectTeam.project_id, ProjectTeam.team_id)):
        teams.setdefault(project_id, []).append(team_id)
    return [
        _to_project_out(p, members.get(p.id, []), teams.get(p.id, []))
        for p in session.scalars(select(Project).order_by(Project.key))
    ]


@router.patch("/admin/projects/{project_id}")
def edit_project(
    project_id: int, body: ProjectPatch, session: SessionDep, actor: Staff
) -> ProjectOut:
    project = _get(session, Project, project_id, "project")
    before = snapshot(project)
    if "manager_id" in body.model_fields_set:
        _check_manager(session, body.manager_id)
    for field in body.model_fields_set:
        value = getattr(body, field)
        if value is not None or field in ("manager_id", "group_name"):
            setattr(project, field, value)
    _audit(session, actor, "project", project, "update", before=before)
    session.commit()
    return _project_out(session, project)


@router.put("/admin/projects/{project_id}/members")
def set_project_members(
    project_id: int, body: UserIds, session: SessionDep, actor: Staff
) -> ProjectOut:
    project = _get(session, Project, project_id, "project")
    _require_all(session, User, body.user_ids, "user")
    before = {
        "member_ids": _ids(session, ProjectMember.user_id, ProjectMember.project_id, project.id)
    }
    _set_links(
        session,
        ProjectMember,
        ProjectMember.project_id,
        project.id,
        ProjectMember.user_id,
        body.user_ids,
    )
    record(
        session,
        actor_id=actor.id,
        entity="project",
        entity_id=project.id,
        action="update",
        before=before,
        after={"member_ids": sorted(set(body.user_ids))},
    )
    session.commit()
    return _project_out(session, project)


@router.put("/admin/projects/{project_id}/teams")
def set_project_teams(
    project_id: int, body: TeamIds, session: SessionDep, actor: Staff
) -> ProjectOut:
    project = _get(session, Project, project_id, "project")
    _require_all(session, Team, body.team_ids, "team")
    before = {"team_ids": _ids(session, ProjectTeam.team_id, ProjectTeam.project_id, project.id)}
    _set_links(
        session, ProjectTeam, ProjectTeam.project_id, project.id, ProjectTeam.team_id, body.team_ids
    )
    record(
        session,
        actor_id=actor.id,
        entity="project",
        entity_id=project.id,
        action="update",
        before=before,
        after={"team_ids": sorted(set(body.team_ids))},
    )
    session.commit()
    return _project_out(session, project)


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None


class TaskOut(BaseModel):
    id: int
    key: str
    title: str


@router.post("/projects/{project_id}/tasks", status_code=201)
def create_task(project_id: int, body: TaskIn, session: SessionDep, user: CurrentUser) -> TaskOut:
    """HR, admin or the project's manager can add a task (key `<project key>-T<n>`)."""
    project = _get(session, Project, project_id, "project")
    if project.manager_id != user.id and not roles_of(session, user.id) & {"hr", "admin"}:
        raise HTTPException(403, "Only HR, an admin or the project manager can add tasks")
    task_list = session.scalars(
        select(TaskList)
        .where(TaskList.project_id == project.id)
        .order_by(TaskList.position, TaskList.id)
    ).first()
    status = session.scalars(
        select(TaskStatus)
        .where(TaskStatus.project_id == project.id)
        .order_by(TaskStatus.position, TaskStatus.id)
    ).first()
    if task_list is None or status is None:
        raise HTTPException(422, "This project has no task list or statuses yet")
    count = session.scalar(
        select(func.count(Task.id))
        .join(TaskList, TaskList.id == Task.task_list_id)
        .where(TaskList.project_id == project.id)
    )
    task = Task(
        task_list_id=task_list.id,
        status_id=status.id,
        key=f"{project.key}-T{(count or 0) + 1}",
        title=body.title,
        description=body.description,
    )
    session.add(task)
    session.flush()
    _audit(session, user, "task", task, "create")
    session.commit()
    return TaskOut(id=task.id, key=task.key, title=task.title)
