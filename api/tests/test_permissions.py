from datetime import date

from conftest import World, add, hdr, submit

from workhub_api.models import RoleAssignment, User


def user_with(w: World, code: str, *roles: str) -> User:
    user = User(employee_code=code, name=code, email=f"{code.lower()}@x.io")
    w.session.add(user)
    w.session.flush()
    w.session.add_all(RoleAssignment(user_id=user.id, role=r) for r in roles)
    w.session.flush()
    return user


def post(w: World, who: User | None, path: str, body: dict[str, object] | None = None) -> int:
    headers = hdr(who) if who else {}
    status: int = w.client.post(path, json=body, headers=headers).status_code
    return status


def delegation_body(to: User) -> dict[str, object]:
    today = date.today().isoformat()
    return {"to_user_id": to.id, "starts_on": today, "ends_on": today}


def test_an_employee_cannot_approve_send_back_or_bulk_approve(world: World) -> None:
    add(world)
    approval_id = submit(world)
    assert post(world, world.emp, f"/approvals/{approval_id}/approve") == 403
    assert post(world, world.emp, f"/approvals/{approval_id}/send-back", {"reason": "x"}) == 403
    assert post(world, world.emp, "/approvals/bulk-approve", {"approval_ids": [approval_id]}) == 403
    assert post(world, None, f"/approvals/{approval_id}/approve") == 401  # not signed in at all
    # Nothing was changed by the refused attempts: the manager can still approve it.
    assert post(world, world.boss, f"/approvals/{approval_id}/approve") == 200


def test_hr_finance_and_admin_alone_cannot_approve_but_a_manager_among_several_roles_can(
    world: World,
) -> None:
    for role in ("hr", "finance", "admin"):
        who = user_with(world, f"ONLY-{role}", role)
        assert post(world, who, "/approvals/1/approve") == 403, role
    nobody = user_with(world, "NOROLES")  # a user with no roles at all
    assert post(world, nobody, "/approvals/1/approve") == 403
    several = user_with(world, "SEVERAL", "employee", "hr", "manager")
    # Past the role check, an approval that doesn't exist is a plain 404.
    assert post(world, several, "/approvals/999999999/approve") == 404


def test_only_managers_can_delegate_and_only_to_managers(world: World) -> None:
    deputy = user_with(world, "DEPUTY", "employee", "manager")
    plain = user_with(world, "PLAIN", "employee")
    assert post(world, world.emp, "/delegations", delegation_body(deputy)) == 403  # not a manager
    assert (
        post(world, world.boss, "/delegations", delegation_body(plain)) == 422
    )  # delegate can't act
    assert post(world, world.boss, "/delegations", delegation_body(deputy)) == 201
    # Looking at your own delegations and the inbox never needs the manager role.
    assert world.client.get("/delegations", headers=hdr(world.emp)).status_code == 200
    assert world.client.get("/approvals/inbox", headers=hdr(world.emp)).status_code == 200
