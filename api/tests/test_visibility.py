"""Task and project privacy (visibility.py): who may log time on a task, who may see a project."""

from conftest import DAY, World, hdr
from sqlalchemy import select

from workhub_api.models import (
    Project,
    ProjectMember,
    ProjectTeam,
    RoleAssignment,
    TaskList,
    TaskOwner,
    Team,
    TeamMember,
    User,
)
from workhub_api.visibility import can_see_project, can_see_task


def project_of(w: World) -> Project:
    return w.session.scalars(
        select(Project)
        .join(TaskList, TaskList.project_id == Project.id)
        .where(TaskList.id == w.task.task_list_id)
    ).one()


def person(w: World, code: str, *, member: bool = False) -> User:
    user = User(employee_code=code, name=code, email=f"{code.lower()}@x.io")
    w.session.add(user)
    w.session.flush()
    if member:
        w.session.add(ProjectMember(project_id=project_of(w).id, user_id=user.id))
        w.session.flush()
    return user


def team_with(w: World, name: str, *users: User) -> Team:
    team = Team(name=name)
    w.session.add(team)
    w.session.flush()
    w.session.add_all(TeamMember(team_id=team.id, user_id=u.id) for u in users)
    w.session.flush()
    return team


def log(w: World, user: User) -> int:
    body = {"work_date": DAY.isoformat(), "minutes": 30, "task_id": w.task.id}
    return int(w.client.post("/time/entries", json=body, headers=hdr(user)).status_code)


def test_a_project_member_can_log_on_an_unassigned_task_but_an_outsider_cannot(
    world: World,
) -> None:
    outsider = person(world, "OUT")
    assert log(world, world.emp) == 201  # emp is a member of the project
    res = world.client.post(
        "/time/entries",
        json={"work_date": DAY.isoformat(), "minutes": 30, "task_id": world.task.id},
        headers=hdr(outsider),
    )
    assert res.status_code == 422 and "not assigned to you" in res.json()["detail"]


def test_an_assigned_task_is_private_to_the_assignees(world: World) -> None:
    colleague = person(world, "COL", member=True)  # on the project, but not assigned
    world.session.add(TaskOwner(task_id=world.task.id, user_id=world.emp.id))
    world.session.flush()
    assert log(world, world.emp) == 201
    assert log(world, colleague) == 422
    assert can_see_task(world.session, colleague, world.task.id) is False


def test_a_task_assigned_to_a_team_is_visible_to_its_members(world: World) -> None:
    colleague = person(world, "COL", member=True)
    team = team_with(world, "Core", world.emp)
    world.session.add(TaskOwner(task_id=world.task.id, team_id=team.id))
    world.session.flush()
    assert log(world, world.emp) == 201
    assert log(world, colleague) == 422
    world.session.add(TeamMember(team_id=team.id, user_id=colleague.id))
    world.session.flush()
    assert log(world, colleague) == 201


def test_the_project_manager_and_admins_see_every_task(world: World) -> None:
    boss_of_project = person(world, "PM")
    admin = person(world, "ADM")
    world.session.add(RoleAssignment(user_id=admin.id, role="admin"))
    project = project_of(world)
    project.manager_id = boss_of_project.id
    world.session.add(TaskOwner(task_id=world.task.id, user_id=world.emp.id))
    world.session.flush()
    assert can_see_task(world.session, boss_of_project, world.task.id) is True
    assert can_see_task(world.session, admin, world.task.id) is True
    assert can_see_task(world.session, person(world, "OTH", member=True), world.task.id) is False


def test_a_project_team_sees_unassigned_tasks(world: World) -> None:
    visitor = person(world, "VIS")
    team = team_with(world, "Visitors", visitor)
    assert can_see_task(world.session, visitor, world.task.id) is False
    world.session.add(ProjectTeam(project_id=project_of(world).id, team_id=team.id))
    world.session.flush()
    assert can_see_task(world.session, visitor, world.task.id) is True


def test_an_unknown_task_is_not_visible(world: World) -> None:
    assert can_see_task(world.session, world.emp, 999999999) is False
    body = {"work_date": DAY.isoformat(), "minutes": 30, "task_id": 999999999}
    assert world.client.post("/time/entries", json=body, headers=hdr(world.emp)).status_code == 422


def test_project_visibility_public_and_private(world: World) -> None:
    project = project_of(world)
    outsider = person(world, "OUT")
    assert can_see_project(world.session, outsider, project.id) is True  # public by default
    project.visibility = "private"
    world.session.flush()
    assert can_see_project(world.session, outsider, project.id) is False
    assert can_see_project(world.session, world.emp, project.id) is True  # a member
    manager = person(world, "PM")
    project.manager_id = manager.id
    admin = person(world, "ADM")
    world.session.add(RoleAssignment(user_id=admin.id, role="admin"))
    team = team_with(world, "Visitors", outsider)
    world.session.flush()
    assert can_see_project(world.session, manager, project.id) is True
    assert can_see_project(world.session, admin, project.id) is True
    world.session.add(ProjectTeam(project_id=project.id, team_id=team.id))
    world.session.flush()
    assert can_see_project(world.session, outsider, project.id) is True  # through a project team
    assert can_see_project(world.session, outsider, 999999999) is False
