"""Sign-in version 1: email and password give a session token, sent as a Bearer header."""

from datetime import UTC, datetime, timedelta

import pytest
from conftest import World, hdr
from httpx import Response
from sqlalchemy import select

from workhub_api.auth import hash_password
from workhub_api.config import settings
from workhub_api.models import AuthSession, Credential

PASSWORD = "pw-1234"


@pytest.fixture
def signed_up(world: World, monkeypatch: pytest.MonkeyPatch) -> World:
    """The employee has a password. The dev header is off, so only real sign-in works."""
    world.session.add(Credential(user_id=world.emp.id, password_hash=hash_password(PASSWORD)))
    world.session.flush()
    monkeypatch.setattr(settings, "dev_auth", False)
    return world


def login(w: World, email: str = "emp@x.io", password: str = PASSWORD) -> Response:
    res: Response = w.client.post("/auth/login", json={"email": email, "password": password})
    return res


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_a_token_that_opens_the_api(signed_up: World) -> None:
    res = login(signed_up)
    assert res.status_code == 200
    token = res.json()["token"]
    me = signed_up.client.get("/auth/me", headers=bearer(token))
    assert me.status_code == 200
    assert me.json() == {
        "id": signed_up.emp.id,
        "name": "Emp",
        "email": "emp@x.io",
        "roles": ["employee"],
    }
    assert signed_up.client.get("/time/week", headers=bearer(token)).status_code == 200


def test_email_is_matched_ignoring_case(signed_up: World) -> None:
    assert login(signed_up, email="EMP@x.io").status_code == 200


def test_wrong_password_and_unknown_email_look_the_same(signed_up: World) -> None:
    wrong = login(signed_up, password="nope")
    unknown = login(signed_up, email="who@x.io")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_user_without_a_password_cannot_sign_in(signed_up: World) -> None:
    assert login(signed_up, email="boss@x.io").status_code == 401


def test_deactivated_user_cannot_sign_in_or_keep_using_a_token(signed_up: World) -> None:
    token = login(signed_up).json()["token"]
    signed_up.emp.active = False
    signed_up.session.flush()
    assert login(signed_up).status_code == 401
    assert signed_up.client.get("/auth/me", headers=bearer(token)).status_code == 401


def test_token_is_stored_only_as_a_hash(signed_up: World) -> None:
    token = login(signed_up).json()["token"]
    stored = signed_up.session.scalars(select(AuthSession.token_hash)).all()
    assert stored and token not in stored


def test_expired_session_is_rejected(signed_up: World) -> None:
    token = login(signed_up).json()["token"]
    for s in signed_up.session.scalars(select(AuthSession)):
        s.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    signed_up.session.flush()
    assert signed_up.client.get("/auth/me", headers=bearer(token)).status_code == 401


def test_logout_ends_the_session(signed_up: World) -> None:
    token = login(signed_up).json()["token"]
    assert signed_up.client.post("/auth/logout", headers=bearer(token)).status_code == 204
    assert signed_up.client.get("/auth/me", headers=bearer(token)).status_code == 401


def test_garbage_and_missing_tokens_are_rejected(signed_up: World) -> None:
    assert signed_up.client.get("/auth/me", headers=bearer("not-a-token")).status_code == 401
    assert signed_up.client.get("/auth/me").status_code == 401


def test_dev_header_is_ignored_when_dev_auth_is_off(signed_up: World) -> None:
    assert signed_up.client.get("/auth/me", headers=hdr(signed_up.emp)).status_code == 401


def test_dev_header_still_works_when_dev_auth_is_on(
    signed_up: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "dev_auth", True)
    assert signed_up.client.get("/auth/me", headers=hdr(signed_up.emp)).status_code == 200


def test_user_can_change_their_own_password(signed_up: World) -> None:
    token = login(signed_up).json()["token"]
    body = {"current_password": PASSWORD, "new_password": "brand-new-9"}
    assert (
        signed_up.client.post("/auth/password", json=body, headers=bearer(token)).status_code == 204
    )
    assert login(signed_up).status_code == 401
    assert login(signed_up, password="brand-new-9").status_code == 200


def test_changing_password_needs_the_current_one(signed_up: World) -> None:
    token = login(signed_up).json()["token"]
    body = {"current_password": "wrong", "new_password": "brand-new-9"}
    assert (
        signed_up.client.post("/auth/password", json=body, headers=bearer(token)).status_code == 400
    )


def test_repeated_failures_lock_the_account_for_a_while(signed_up: World) -> None:
    for _ in range(5):
        assert login(signed_up, password="nope").status_code == 401
    assert login(signed_up).status_code == 429  # even the right password waits
