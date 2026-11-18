"""Active users for pickers (delegate to, HR corrections)."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from workhub_api.db import CurrentUser, SessionDep
from workhub_api.models import User

router = APIRouter(prefix="/users", tags=["users"])


class UserPick(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


@router.get("", response_model=list[UserPick])
def list_users(session: SessionDep, _: CurrentUser) -> list[User]:
    return list(session.scalars(select(User).where(User.active).order_by(User.name)))
