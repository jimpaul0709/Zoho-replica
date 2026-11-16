from collections.abc import Iterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from workhub_api.db import engine
from workhub_api.models import Location, Project, RoleAssignment, Team, User
from workhub_api.seed import seed


@pytest.fixture
def session() -> Iterator[Session]:
    conn = engine.connect()
    outer = conn.begin()
    s = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield s
    finally:
        s.close()
        outer.rollback()
        conn.close()


def count(s: Session, model: type) -> int:
    return int(s.scalar(select(func.count()).select_from(model)) or 0)


def test_seed_builds_a_usable_company_and_is_safe_to_repeat(session: Session) -> None:
    models = (User, Location, Team, Project)
    before = [count(session, m) for m in models]
    if not seed(session):
        pytest.skip("the shared database already has the sample data")
    added = [count(session, m) - b for m, b in zip(models, before, strict=True)]
    assert added == [3, 2, 3, 1]
    assert not seed(session)  # second run adds nothing
    assert count(session, User) == before[0] + 3

    users = {
        u.name: u for u in session.scalars(select(User).where(User.employee_code.like("AMP%")))
    }
    assert set(users) == {"Jim", "Jana", "Jay"}
    roles = set(
        session.scalars(
            select(RoleAssignment.role).where(
                RoleAssignment.user_id.in_(u.id for u in users.values())
            )
        )
    )
    assert roles == {"employee", "manager", "hr", "finance", "admin"}
    # The chain is Jim -> Jana -> Jay, and Jay is the top.
    assert users["Jay"].manager_id is None
    assert users["Jana"].manager_id == users["Jay"].id
    assert users["Jim"].manager_id == users["Jana"].id
