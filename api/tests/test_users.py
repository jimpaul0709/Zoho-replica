from conftest import World, hdr

from workhub_api.models import User


def test_lists_active_users_only(world: World) -> None:
    world.session.add(User(employee_code="G1", name="Gone", email="gone@x.io", active=False))
    world.session.flush()
    res = world.client.get("/users", headers=hdr(world.emp))
    assert res.status_code == 200
    emails = {u["email"] for u in res.json()}
    assert {"emp@x.io", "boss@x.io"} <= emails and "gone@x.io" not in emails
    assert set(res.json()[0]) == {"id", "name", "email"}
