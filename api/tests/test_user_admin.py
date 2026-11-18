"""User administration (HR and admin): create staff, set passwords and roles, edit, deactivate."""

from datetime import date
from typing import Any

from conftest import World, hdr
from httpx import Response
from sqlalchemy import select
from test_hr import hr_person

from workhub_api.models import AuditEvent, RoleAssignment, User

PASSWORD = "first-pass-1"


def make_admin(w: World) -> User:
    admin = hr_person(w, "AD1")
    w.session.add(RoleAssignment(user_id=admin.id, role="admin"))
    w.session.flush()
    return admin


def new_user(w: World, who: User, **fields: Any) -> Response:
    body = {
        "employee_code": "NEW1",
        "name": "New One",
        "email": "new1@x.io",
        "password": PASSWORD,
        **fields,
    }
    res: Response = w.client.post("/admin/users", json=body, headers=hdr(who))
    return res


def login(w: World, email: str = "new1@x.io", password: str = PASSWORD) -> Response:
    res: Response = w.client.post("/auth/login", json={"email": email, "password": password})
    return res


def patch(w: World, who: User, user_id: int, **fields: Any) -> Response:
    res: Response = w.client.patch(f"/admin/users/{user_id}", json=fields, headers=hdr(who))
    return res


def test_hr_creates_a_user_who_can_sign_in_and_must_change_the_password(world: World) -> None:
    hr = hr_person(world)
    res = new_user(world, hr, manager_id=world.boss.id, roles=["employee", "manager"])
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["employee_code"] == "NEW1" and body["active"] is True
    assert body["roles"] == ["employee", "manager"] and body["manager_id"] == world.boss.id
    assert "password" not in body and "password_hash" not in body
    first = login(world)
    assert first.status_code == 200 and first.json()["must_change"] is True
    token = first.json()["token"]
    change = {"current_password": PASSWORD, "new_password": "second-pass-2"}
    auth = {"Authorization": f"Bearer {token}"}
    assert world.client.post("/auth/password", json=change, headers=auth).status_code == 204
    assert login(world, password="second-pass-2").json()["must_change"] is False


def test_new_user_gets_the_employee_role_by_default(world: World) -> None:
    assert new_user(world, hr_person(world)).json()["roles"] == ["employee"]


def test_only_hr_or_admin_can_manage_users(world: World) -> None:
    assert new_user(world, world.emp).status_code == 403
    assert world.client.get("/admin/users", headers=hdr(world.emp)).status_code == 403


def test_duplicate_code_or_email_is_refused(world: World) -> None:
    hr = hr_person(world)
    assert new_user(world, hr).status_code == 201
    assert new_user(world, hr, email="other@x.io").status_code == 409  # same code
    assert new_user(world, hr, employee_code="NEW2", email="NEW1@x.io").status_code == 409


def test_manager_must_exist_and_be_active(world: World) -> None:
    hr = hr_person(world)
    assert new_user(world, hr, manager_id=999999).status_code == 422
    world.boss.active = False
    world.session.flush()
    assert new_user(world, hr, manager_id=world.boss.id).status_code == 422


def test_unknown_role_or_short_password_is_refused(world: World) -> None:
    hr = hr_person(world)
    assert new_user(world, hr, roles=["employee", "wizard"]).status_code == 422
    assert new_user(world, hr, password="short").status_code == 422


def test_manager_chain_cannot_loop(world: World) -> None:
    hr = hr_person(world)
    # boss manages emp; making emp the boss's manager would close a loop
    assert patch(world, hr, world.boss.id, manager_id=world.emp.id).status_code == 422
    assert patch(world, hr, world.emp.id, manager_id=world.emp.id).status_code == 422
    assert patch(world, hr, world.emp.id, manager_id=None).status_code == 200


def test_patch_changes_only_the_fields_sent(world: World) -> None:
    hr = hr_person(world)
    res = patch(world, hr, world.emp.id, designation="Engineer")
    assert res.status_code == 200
    body = res.json()
    assert body["designation"] == "Engineer" and body["manager_id"] == world.boss.id
    assert body["name"] == "Emp"


def test_hr_cannot_grant_admin_but_an_admin_can(world: World) -> None:
    hr, admin = hr_person(world), make_admin(world)
    url = f"/admin/users/{world.emp.id}/roles"
    roles = {"roles": ["employee", "admin"]}
    assert world.client.put(url, json=roles, headers=hdr(hr)).status_code == 403
    res = world.client.put(url, json=roles, headers=hdr(admin))
    assert res.status_code == 200 and res.json()["roles"] == ["admin", "employee"]
    # and HR cannot strip an admin's role either
    back = {"roles": ["employee"]}
    assert world.client.put(url, json=back, headers=hdr(hr)).status_code == 403


def test_hr_can_set_ordinary_roles(world: World) -> None:
    hr = hr_person(world)
    url = f"/admin/users/{world.emp.id}/roles"
    res = world.client.put(url, json={"roles": ["employee", "finance"]}, headers=hdr(hr))
    assert res.status_code == 200 and res.json()["roles"] == ["employee", "finance"]


def test_password_reset_signs_the_person_out_and_clears_a_lock(world: World) -> None:
    hr = hr_person(world)
    new_user(world, hr)
    token = login(world).json()["token"]
    for _ in range(5):
        login(world, password="wrong")
    assert login(world).status_code == 429
    user_id = world.session.scalars(select(User.id).where(User.email == "new1@x.io")).one()
    url = f"/admin/users/{user_id}/password"
    res = world.client.post(url, json={"password": "reset-pass-3"}, headers=hdr(hr))
    assert res.status_code == 204
    me = world.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 401
    assert login(world, password=PASSWORD).status_code == 401
    again = login(world, password="reset-pass-3")
    assert again.status_code == 200 and again.json()["must_change"] is True


def test_hr_cannot_take_over_an_admin_account(world: World) -> None:
    hr, admin = hr_person(world), make_admin(world)
    url = f"/admin/users/{admin.id}/password"
    assert (
        world.client.post(url, json={"password": "hijack-pass-9"}, headers=hdr(hr)).status_code
        == 403
    )
    assert (
        world.client.post(url, json={"password": "own-reset-9"}, headers=hdr(admin)).status_code
        == 204
    )


def test_deactivating_ends_access_and_records_the_exit(world: World) -> None:
    hr = hr_person(world)
    new_user(world, hr)
    token = login(world).json()["token"]
    user_id = world.session.scalars(select(User.id).where(User.email == "new1@x.io")).one()
    res = patch(world, hr, user_id, active=False)
    assert res.status_code == 200
    assert res.json()["active"] is False and res.json()["exited_on"] == date.today().isoformat()
    assert login(world).status_code == 401
    me = world.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 401


def test_nobody_can_deactivate_themselves(world: World) -> None:
    hr = hr_person(world)
    assert patch(world, hr, hr.id, active=False).status_code == 422


def test_list_shows_users_with_roles(world: World) -> None:
    hr = hr_person(world)
    rows = world.client.get("/admin/users", headers=hdr(hr)).json()
    by_code = {r["employee_code"]: r for r in rows}
    assert by_code["B1"]["roles"] == ["employee", "manager"]
    assert by_code["E1"]["manager_id"] == world.boss.id


def test_changes_are_audited(world: World) -> None:
    hr = hr_person(world)
    new_user(world, hr)
    user_id = world.session.scalars(select(User.id).where(User.email == "new1@x.io")).one()
    patch(world, hr, user_id, designation="Lead")
    events = world.session.scalars(
        select(AuditEvent).where(AuditEvent.entity == "app_user", AuditEvent.entity_id == user_id)
    ).all()
    assert [e.action for e in events] == ["create", "update"]
    assert all(e.actor_id == hr.id for e in events)
    assert "password" not in str(events[0].after)  # secrets never reach the audit log
