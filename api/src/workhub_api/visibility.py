"""Who can see a project or a task (privacy rules, design section 4).

- Admins and the project's manager see the whole project and every task in it.
- A task that is assigned (to people, or to teams) is visible only to those people, the members
  of those teams, the project's manager and admins.
- A task nobody is assigned to is visible to the project's members (directly or through a team).
- A project is visible to its manager, its members, the members of its teams and admins; a public
  project is visible to everyone.

Time can only be logged on a task you can see. Any list of projects or tasks must use these same
functions, so the rules live in one place. Each check is a single database round trip.
"""

from sqlalchemy import ColumnElement, exists, or_, select
from sqlalchemy.orm import Session

from workhub_api.models import (
    Project,
    ProjectMember,
    ProjectTeam,
    RoleAssignment,
    Task,
    TaskList,
    TaskOwner,
    TeamMember,
    User,
)


def _admin(user_id: int) -> ColumnElement[bool]:
    return exists().where(RoleAssignment.user_id == user_id, RoleAssignment.role == "admin")


def _member(user_id: int) -> ColumnElement[bool]:
    """On the project directly, or through one of its teams (correlates to `Project`)."""
    mine = select(TeamMember.team_id).where(TeamMember.user_id == user_id)
    return or_(
        exists().where(ProjectMember.project_id == Project.id, ProjectMember.user_id == user_id),
        exists().where(ProjectTeam.project_id == Project.id, ProjectTeam.team_id.in_(mine)),
    )


def can_see_project(session: Session, user: User, project_id: int) -> bool:
    row = session.execute(
        select(
            Project.visibility,
            (Project.manager_id == user.id).label("manager"),
            _admin(user.id).label("admin"),
            _member(user.id).label("member"),
        ).where(Project.id == project_id)
    ).first()
    if row is None:
        return False
    visibility, manager, admin, member = row
    return bool(visibility == "public" or manager or admin or member)


def can_see_task(session: Session, user: User, task_id: int) -> bool:
    mine = select(TeamMember.team_id).where(TeamMember.user_id == user.id)
    row = session.execute(
        select(
            (Project.manager_id == user.id).label("manager"),
            _admin(user.id).label("admin"),
            exists().where(TaskOwner.task_id == Task.id).label("assigned"),
            exists()
            .where(
                TaskOwner.task_id == Task.id,
                or_(TaskOwner.user_id == user.id, TaskOwner.team_id.in_(mine)),
            )
            .label("assigned_to_me"),
            _member(user.id).label("member"),
        )
        .select_from(Task)
        .join(TaskList, TaskList.id == Task.task_list_id)
        .join(Project, Project.id == TaskList.project_id)
        .where(Task.id == task_id)
    ).first()
    if row is None:
        return False
    manager, admin, assigned, assigned_to_me, member = row
    return bool(manager or admin or (assigned_to_me if assigned else member))
