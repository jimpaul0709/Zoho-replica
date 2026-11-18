"""Org admin (HR and admin): locations, holidays, teams, charge codes, projects and tasks."""

from typing import Any

import pytest
from conftest import World, hdr
from httpx import Response
from sqlalchemy import select
from test_hr import hr_person

from workhub_api.models import AuditEvent, TaskList, TaskStatus, User


def post(w: World, who: User, path: str, **body: Any) -> Response:
    res: Response = w.client.post(path, json=body, headers=hdr(who))
    return res


def put(w: World, who: User, path: str, **body: Any) -> Response:
    res: Response = w.client.put(path, json=body, headers=hdr(who))
    return res


def get(w: World, who: User, path: str) -> Any:
    res = w.client.get(path, headers=hdr(who))
    assert res.status_code == 200, res.text
    return res.json()


def targets(w: World, who: User) -> dict[str, Any]:
    data: dict[str, Any] = get(w, who, "/time/targets")
    return data


def make_team(w: World, hr: User, name: str = "T-Team", users: list[int] | None = None) -> int:
    team_id: int = post(w, hr, "/admin/teams", name=name).json()["id"]
    if users:
        assert put(w, hr, f"/admin/teams/{team_id}/members", user_ids=users).status_code == 200
    return team_id


def make_project(w: World, hr: User, key: str = "TP-1", **fields: Any) -> dict[str, Any]:
    res = post(w, hr, "/admin/projects", key=key, name="Test project", **fields)
    assert res.status_code == 201, res.text
    body: dict[str, Any] = res.json()
    return body


# ---------- who may use it ----------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/admin/locations"),
        ("get", "/admin/locations"),
        ("post", "/admin/holidays"),
        ("post", "/admin/teams"),
        ("get", "/admin/teams"),
        ("post", "/admin/charge-codes"),
        ("get", "/admin/charge-codes"),
        ("post", "/admin/projects"),
        ("get", "/admin/projects"),
    ],
)
def test_ordinary_employees_are_refused(world: World, method: str, path: str) -> None:
    res = world.client.request(method, path, json={}, headers=hdr(world.emp))
    assert res.status_code == 403


# ---------- locations and holidays ----------


def test_locations_and_holidays(world: World) -> None:
    hr = hr_person(world)
    loc = post(world, hr, "/admin/locations", name="T-Pune")
    assert loc.status_code == 201
    loc_id = loc.json()["id"]
    assert post(world, hr, "/admin/locations", name="T-Pune").status_code == 409
    assert "T-Pune" in [row["name"] for row in get(world, hr, "/admin/locations")]

    day = {"location_id": loc_id, "on_date": "2027-03-10", "name": "T-Holi"}
    made = post(world, hr, "/admin/holidays", **day)
    assert made.status_code == 201
    assert post(world, hr, "/admin/holidays", **day).status_code == 409
    assert post(world, hr, "/admin/holidays", **{**day, "location_id": 999999}).status_code == 422
    rows = get(world, hr, f"/admin/holidays?location_id={loc_id}")
    assert [(r["on_date"], r["name"]) for r in rows] == [("2027-03-10", "T-Holi")]
    gone = world.client.delete(f"/admin/holidays/{made.json()['id']}", headers=hdr(hr))
    assert gone.status_code == 204
    assert get(world, hr, f"/admin/holidays?location_id={loc_id}") == []


# ---------- teams ----------


def test_team_members_are_replaced_not_added_to(world: World) -> None:
    hr = hr_person(world)
    team_id = make_team(world, hr, users=[world.emp.id, world.boss.id])
    assert post(world, hr, "/admin/teams", name="T-Team").status_code == 409
    teams = {t["name"]: t for t in get(world, hr, "/admin/teams")}
    assert sorted(teams["T-Team"]["user_ids"]) == sorted([world.emp.id, world.boss.id])
    url = f"/admin/teams/{team_id}/members"
    assert put(world, hr, url, user_ids=[world.emp.id]).status_code == 200
    teams = {t["name"]: t for t in get(world, hr, "/admin/teams")}
    assert teams["T-Team"]["user_ids"] == [world.emp.id]
    assert put(world, hr, url, user_ids=[999999]).status_code == 422
    assert put(world, hr, "/admin/teams/999999/members", user_ids=[]).status_code == 404


# ---------- charge codes ----------


def test_charge_code_shows_up_for_the_team_it_is_shared_with(world: World) -> None:
    hr = hr_person(world)
    team_id = make_team(world, hr, users=[world.emp.id])
    res = post(world, hr, "/admin/charge-codes", code="T-Code", name="Test", team_ids=[team_id])
    assert res.status_code == 201, res.text
    code_id = res.json()["id"]
    assert res.json()["team_ids"] == [team_id] and res.json()["active"] is True
    assert "T-Code" in [c["code"] for c in targets(world, world.emp)["charge_codes"]]
    assert targets(world, world.boss)["charge_codes"] == []  # not in the team
    off = world.client.patch(
        f"/admin/charge-codes/{code_id}", json={"active": False}, headers=hdr(hr)
    )
    assert off.status_code == 200 and off.json()["active"] is False
    assert "T-Code" not in [c["code"] for c in targets(world, world.emp)["charge_codes"]]


def test_charge_code_rules(world: World) -> None:
    hr = hr_person(world)
    assert post(world, hr, "/admin/charge-codes", code="T-Code", name="A").status_code == 201
    assert post(world, hr, "/admin/charge-codes", code="t-code", name="B").status_code == 409
    unknown = post(world, hr, "/admin/charge-codes", code="T-X", name="B", team_ids=[999999])
    assert unknown.status_code == 422
    code = next(c for c in get(world, hr, "/admin/charge-codes") if c["code"] == "T-Code")
    team_id = make_team(world, hr)
    url = f"/admin/charge-codes/{code['id']}/teams"
    assert put(world, hr, url, team_ids=[team_id]).status_code == 200
    assert put(world, hr, url, team_ids=[]).json()["team_ids"] == []


# ---------- projects and tasks ----------


def test_new_project_starts_with_statuses_and_a_backlog(world: World) -> None:
    hr = hr_person(world)
    project = make_project(world, hr, manager_id=world.boss.id)
    assert project["key"] == "TP-1" and project["manager_id"] == world.boss.id
    assert project["visibility"] == "public" and project["member_ids"] == []
    statuses = world.session.scalars(
        select(TaskStatus.name)
        .where(TaskStatus.project_id == project["id"])
        .order_by(TaskStatus.position)
    ).all()
    assert list(statuses) == ["Open", "In progress", "Done"]
    lists = world.session.scalars(
        select(TaskList.name).where(TaskList.project_id == project["id"])
    ).all()
    assert list(lists) == ["Backlog"]


def test_project_rules(world: World) -> None:
    hr = hr_person(world)
    make_project(world, hr)
    assert post(world, hr, "/admin/projects", key="tp-1", name="Dup").status_code == 409
    nobody = post(world, hr, "/admin/projects", key="TP-2", name="X", manager_id=999999)
    assert nobody.status_code == 422
    bad = post(world, hr, "/admin/projects", key="TP-3", name="X", visibility="secret")
    assert bad.status_code == 422


def test_task_keys_count_up_and_default_to_the_first_status(world: World) -> None:
    hr = hr_person(world)
    project = make_project(world, hr)
    url = f"/projects/{project['id']}/tasks"
    one = post(world, hr, url, title="First")
    two = post(world, hr, url, title="Second")
    assert (one.status_code, two.status_code) == (201, 201)
    assert (one.json()["key"], two.json()["key"]) == ("TP-1-T1", "TP-1-T2")
    assert post(world, hr, url, title="").status_code == 422
    assert post(world, hr, "/projects/999999/tasks", title="X").status_code == 404


def test_project_manager_can_add_tasks_but_other_employees_cannot(world: World) -> None:
    hr = hr_person(world)
    project = make_project(world, hr, manager_id=world.boss.id)
    url = f"/projects/{project['id']}/tasks"
    assert post(world, world.boss, url, title="By the manager").status_code == 201
    assert post(world, world.emp, url, title="By someone else").status_code == 403


def test_members_see_the_projects_tasks_in_the_picker(world: World) -> None:
    hr = hr_person(world)
    project = make_project(world, hr)
    task = post(world, hr, f"/projects/{project['id']}/tasks", title="Shared work").json()
    seen = [t["key"] for t in targets(world, world.boss)["tasks"]]
    assert task["key"] not in seen  # not a member yet
    url = f"/admin/projects/{project['id']}/members"
    res = put(world, hr, url, user_ids=[world.boss.id])
    assert res.status_code == 200 and res.json()["member_ids"] == [world.boss.id]
    assert task["key"] in [t["key"] for t in targets(world, world.boss)["tasks"]]
    assert put(world, hr, url, user_ids=[999999]).status_code == 422


def test_a_team_on_a_project_gives_its_members_access(world: World) -> None:
    hr = hr_person(world)
    project = make_project(world, hr)
    task = post(world, hr, f"/projects/{project['id']}/tasks", title="Team work").json()
    team_id = make_team(world, hr, users=[world.boss.id])
    url = f"/admin/projects/{project['id']}/teams"
    res = put(world, hr, url, team_ids=[team_id])
    assert res.status_code == 200 and res.json()["team_ids"] == [team_id]
    assert task["key"] in [t["key"] for t in targets(world, world.boss)["tasks"]]
    assert put(world, hr, url, team_ids=[999999]).status_code == 422


def test_project_can_be_edited_and_listed(world: World) -> None:
    hr = hr_person(world)
    project = make_project(world, hr)
    res = world.client.patch(
        f"/admin/projects/{project['id']}",
        json={"status": "closed", "visibility": "private", "name": "Renamed"},
        headers=hdr(hr),
    )
    assert res.status_code == 200
    assert (res.json()["status"], res.json()["visibility"], res.json()["name"]) == (
        "closed",
        "private",
        "Renamed",
    )
    assert res.json()["key"] == "TP-1"
    listed = {p["key"]: p for p in get(world, hr, "/admin/projects")}
    assert listed["TP-1"]["name"] == "Renamed"


# ---------- audit ----------


def test_every_create_is_audited(world: World) -> None:
    hr = hr_person(world)
    team_id = make_team(world, hr)
    project = make_project(world, hr)
    task = post(world, hr, f"/projects/{project['id']}/tasks", title="T").json()
    code_id = post(world, hr, "/admin/charge-codes", code="T-Code", name="C").json()["id"]
    seen = {
        (e.entity, e.entity_id, e.action)
        for e in world.session.scalars(select(AuditEvent).where(AuditEvent.actor_id == hr.id))
    }
    assert ("team", team_id, "create") in seen
    assert ("project", project["id"], "create") in seen
    assert ("task", task["id"], "create") in seen
    assert ("charge_code", code_id, "create") in seen
