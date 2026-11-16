"""Microsoft sign-in (entra_auth.py, not wired into the app): a bearer token is checked and
mapped to a WorkHub user by email.

Tokens are signed here with a throwaway RSA key and the key lookup is swapped in, so no network.
The Entra router is mounted on a small app of its own, since the real app does not include it.
"""

import time
from types import SimpleNamespace

import jwt
import pytest
from conftest import World
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from workhub_api import entra_auth
from workhub_api.db import get_session

TENANT, CLIENT = "tenant-1", "client-1"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def entra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(entra_auth.entra, "entra_tenant_id", TENANT)
    monkeypatch.setattr(entra_auth.entra, "entra_client_id", CLIENT)
    signing_key = SimpleNamespace(key=KEY.public_key())
    fake = SimpleNamespace(get_signing_key_from_jwt=lambda _t: signing_key)
    monkeypatch.setattr(entra_auth, "_jwks", lambda: fake)


def me(world: World, headers: dict[str, str] | None = None) -> Response:
    """Call /me on a throwaway app that has only the Entra router, on the test's session."""
    app = FastAPI()
    app.include_router(entra_auth.router)
    app.dependency_overrides[get_session] = lambda: world.session
    res: Response = TestClient(app).get("/me", headers=headers)
    return res


def token(email: str = "boss@x.io", aud: str = CLIENT, exp: int = 3600) -> dict[str, str]:
    claims = {
        "aud": aud,
        "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0",
        "exp": int(time.time()) + exp,
        "preferred_username": email,
    }
    return {"Authorization": "Bearer " + jwt.encode(claims, KEY, algorithm="RS256")}


def test_valid_token_returns_the_matching_user(world: World) -> None:
    res = me(world, token())
    assert res.status_code == 200
    assert res.json() == {"name": "Boss", "email": "boss@x.io", "roles": ["employee", "manager"]}


def test_email_match_ignores_case(world: World) -> None:
    assert me(world, token("BOSS@X.io")).status_code == 200


def test_api_style_audience_is_accepted(world: World) -> None:
    assert me(world, token(aud=f"api://{CLIENT}")).status_code == 200


def test_wrong_audience_is_rejected(world: World) -> None:
    assert me(world, token(aud="someone-else")).status_code == 401


def test_expired_token_is_rejected(world: World) -> None:
    assert me(world, token(exp=-10)).status_code == 401


def test_email_without_a_workhub_account_is_forbidden(world: World) -> None:
    assert me(world, token("stranger@x.io")).status_code == 403


def test_no_token_is_unauthorized(world: World) -> None:
    assert me(world).status_code == 401
