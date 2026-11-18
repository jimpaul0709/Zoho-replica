"""GET /time/targets: what the week grid may log time on (visible tasks, shared charge codes)."""

from conftest import World, hdr

from workhub_api.models import ChargeCodeTeam, Task, Team, TeamMember
from workhub_api.visibility import can_see_task


def targets(w: World, who: str = "emp") -> dict[str, list[dict[str, object]]]:
    user = w.emp if who == "emp" else w.boss
    res = w.client.get("/time/targets", headers=hdr(user))
    assert res.status_code == 200
    data: dict[str, list[dict[str, object]]] = res.json()
    return data


def test_member_sees_the_task_with_its_project(world: World) -> None:
    tasks = targets(world)["tasks"]
    assert tasks == [
        {
            "id": world.task.id,
            "key": "P-1-T1",
            "title": "T",
            "project_key": "P-1",
            "project_name": "P",
        }
    ]


def test_non_member_does_not_see_the_task(world: World) -> None:
    assert targets(world, "boss")["tasks"] == []


def test_list_agrees_with_the_single_task_check(world: World) -> None:
    """The list is one query; can_see_task is per task. They must never disagree."""
    for user in (world.emp, world.boss):
        listed = {t["id"] for t in targets(world, "emp" if user is world.emp else "boss")["tasks"]}
        every = {t.id for t in world.session.query(Task).all()}
        assert listed == {i for i in every if can_see_task(world.session, user, i)}


def test_charge_code_appears_only_when_shared_with_my_team(world: World) -> None:
    assert targets(world)["charge_codes"] == []
    team = Team(name="T-Team")
    world.session.add(team)
    world.session.flush()
    world.session.add_all(
        [
            TeamMember(team_id=team.id, user_id=world.emp.id),
            ChargeCodeTeam(charge_code_id=world.code.id, team_id=team.id),
        ]
    )
    world.session.flush()
    assert targets(world)["charge_codes"] == [
        {"id": world.code.id, "code": "T-Bench", "name": "T-Bench"}
    ]
    world.code.active = False
    world.session.flush()
    assert targets(world)["charge_codes"] == []


def test_needs_sign_in(world: World) -> None:
    assert world.client.get("/time/targets").status_code in (401, 403)
