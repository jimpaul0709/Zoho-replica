"""Role checks (design section 4: permissions are enforced in the API, the UI only hides things).

Roles are employee, manager, hr, finance and admin. A user can hold several (`role_assignment`).
Use it as a dependency on an endpoint:

    def approve(..., user: Manager): ...                       # must be a manager
    def upload(..., user: User = Depends(require_roles("hr")))  # or any of several roles

Someone without a needed role gets 403. No sign-in at all still gets 401 (see db.current_user).
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from workhub_api.db import CurrentUser, SessionDep
from workhub_api.models import RoleAssignment, User


def roles_of(session: Session, user_id: int) -> set[str]:
    return set(
        session.scalars(select(RoleAssignment.role).where(RoleAssignment.user_id == user_id))
    )


def require_roles(*allowed: str) -> Callable[..., User]:
    """A dependency that lets the request through only if the user holds one of `allowed`."""

    def check(session: SessionDep, user: CurrentUser) -> User:
        if not roles_of(session, user.id) & set(allowed):
            raise HTTPException(403, "You need the " + " or ".join(allowed) + " role for this")
        return user

    return check


Manager = Annotated[User, Depends(require_roles("manager"))]
