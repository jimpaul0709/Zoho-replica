"""Microsoft sign-in: a bearer token is checked and mapped to a WorkHub user by email.

Tokens are signed here with a throwaway RSA key and the key lookup is swapped in, so no network.
"""

import time
from types import SimpleNamespace

import jwt
import pytest
from conftest import World
from cryptography.hazmat.primitives.asymmetric import rsa

from workhub_api import db
from workhub_api.config import settings

TENANT, CLIENT = "tenant-1", "client-1"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def entra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "entra_tenant_id", TENANT)
    monkeypatch.setattr(settings, "entra_client_id", CLIENT)
    signing_key = SimpleNamespace(key=KEY.public_key())
    fake = SimpleNamespace(get_signing_key_from_jwt=lambda _t: signing_key)
    monkeypatch.setattr(db, "_jwks", lambda: fake)


def token(email: str = "boss@x.io", aud: str = CLIENT, exp: int = 3600) -> dict[str, str]:
    claims = {
        "aud": aud,
        "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0",
        "exp": int(time.time()) + exp,
        "preferred_username": email,
    }
    return {"Authorization": "Bearer " + jwt.encode(claims, KEY, algorithm="RS256")}


def test_valid_token_returns_the_matching_user(world: World) -> None:
    res = world.client.get("/me", headers=token())
    assert res.status_code == 200
    assert res.json() == {"name": "Boss", "email": "boss@x.io", "roles": ["employee", "manager"]}


def test_email_match_ignores_case(world: World) -> None:
    assert world.client.get("/me", headers=token("BOSS@X.io")).status_code == 200


def test_api_style_audience_is_accepted(world: World) -> None:
    assert world.client.get("/me", headers=token(aud=f"api://{CLIENT}")).status_code == 200


def test_wrong_audience_is_rejected(world: World) -> None:
    assert world.client.get("/me", headers=token(aud="someone-else")).status_code == 401


def test_expired_token_is_rejected(world: World) -> None:
    assert world.client.get("/me", headers=token(exp=-10)).status_code == 401


def test_email_without_a_workhub_account_is_forbidden(world: World) -> None:
    assert world.client.get("/me", headers=token("stranger@x.io")).status_code == 403


def test_no_token_and_no_dev_auth_is_unauthorized(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "dev_auth", False)
    assert world.client.get("/me").status_code == 401
