"""Payslips (WH-50, WH-51): HR uploads a month, previews the matching, publishes; employees
see and download only their own, and every download is audited."""

import io
import zipfile
from typing import Any

import pytest
from conftest import World, hdr
from httpx import Response
from sqlalchemy import select
from test_hr import hr_person

from workhub_api.models import AuditEvent, Payslip, User

MONTH = "2026-11"


def pdf(text: str = "emp") -> bytes:
    return b"%PDF-1.4\n" + text.encode() + b"\n%%EOF"


def upload(
    w: World, files: dict[str, bytes], month: str = MONTH, who: User | None = None
) -> Response:
    parts = [("files", (name, data, "application/octet-stream")) for name, data in files.items()]
    res: Response = w.client.post(
        "/payslips/batches",
        data={"month": month},
        files=parts,
        headers=hdr(who or hr_person(w)),
    )
    return res


def zipped(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def publish(w: World, batch_id: int, hr: User) -> Response:
    res: Response = w.client.post(f"/payslips/batches/{batch_id}/publish", headers=hdr(hr))
    return res


def mine(w: World, user: User) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = w.client.get("/payslips/mine", headers=hdr(user)).json()
    return rows


def test_upload_matches_files_to_employees_by_code(world: World) -> None:
    res = upload(world, {"E1_nov.pdf": pdf("emp"), "b1_nov.PDF": pdf("boss")})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["month"] == MONTH and body["status"] == "draft"
    assert sorted(m["employee_code"] for m in body["matched"]) == ["B1", "E1"]
    assert body["unmatched"] == [] and body["duplicates"] == []


def test_unmatched_files_say_why_and_are_not_stored(world: World) -> None:
    res = upload(
        world,
        {"ZZ9_nov.pdf": pdf(), "notes.pdf": pdf(), "E1_nov.txt": pdf(), "B1_nov.pdf": b"not a pdf"},
    )
    body = res.json()
    assert body["matched"] == []
    reasons = {u["filename"]: u["reason"] for u in body["unmatched"]}
    assert set(reasons) == {"ZZ9_nov.pdf", "notes.pdf", "E1_nov.txt", "B1_nov.pdf"}
    assert "no employee" in reasons["ZZ9_nov.pdf"].lower()
    assert "not a pdf" in reasons["B1_nov.pdf"].lower()


def test_two_files_for_one_person_are_reported_and_neither_is_kept(world: World) -> None:
    body = upload(world, {"E1_a.pdf": pdf("a"), "E1_b.pdf": pdf("b"), "B1_a.pdf": pdf()}).json()
    assert [m["employee_code"] for m in body["matched"]] == ["B1"]
    assert body["duplicates"] == [{"employee_code": "E1", "filenames": ["E1_a.pdf", "E1_b.pdf"]}]


def test_zip_is_opened_and_folders_are_ignored(world: World) -> None:
    archive = zipped({"nov/E1_nov.pdf": pdf("emp"), "nov/readme.txt": b"hi"})
    body = upload(world, {"payslips.zip": archive}).json()
    assert [m["employee_code"] for m in body["matched"]] == ["E1"]
    assert [u["filename"] for u in body["unmatched"]] == ["readme.txt"]


def test_only_hr_can_upload_preview_or_publish(world: World) -> None:
    assert upload(world, {"E1_a.pdf": pdf()}, who=world.emp).status_code == 403
    batch_id = upload(world, {"E1_a.pdf": pdf()}).json()["id"]
    got = world.client.get(f"/payslips/batches/{batch_id}", headers=hdr(world.emp))
    assert got.status_code == 403
    assert publish(world, batch_id, world.emp).status_code == 403


def test_bad_month_is_rejected(world: World) -> None:
    hr = hr_person(world)
    assert upload(world, {"E1_a.pdf": pdf()}, month="Nov 2026", who=hr).status_code == 422
    assert upload(world, {"E1_a.pdf": pdf()}, month="2026-13", who=hr).status_code == 422


def test_oversized_file_is_unmatched(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    import workhub_api.payslips as payslips

    monkeypatch.setattr(payslips, "MAX_FILE_BYTES", 20)
    body = upload(world, {"E1_a.pdf": pdf("x" * 100)}).json()
    assert body["matched"] == []
    assert "too large" in body["unmatched"][0]["reason"].lower()


def test_preview_shows_the_same_report(world: World) -> None:
    hr = hr_person(world)
    created = upload(world, {"E1_a.pdf": pdf(), "ZZ9_a.pdf": pdf()}, who=hr).json()
    got = world.client.get(f"/payslips/batches/{created['id']}", headers=hdr(hr)).json()
    assert got == created


def test_employee_sees_nothing_until_it_is_published(world: World) -> None:
    hr = hr_person(world)
    batch_id = upload(world, {"E1_a.pdf": pdf()}, who=hr).json()["id"]
    assert mine(world, world.emp) == []
    assert publish(world, batch_id, hr).status_code == 200
    rows = mine(world, world.emp)
    assert [r["month"] for r in rows] == [MONTH]
    assert mine(world, world.boss) == []  # no file for the boss


def test_publish_twice_or_an_empty_batch_is_refused(world: World) -> None:
    hr = hr_person(world)
    empty = upload(world, {"ZZ9_a.pdf": pdf()}, month="2026-10", who=hr).json()["id"]
    assert publish(world, empty, hr).status_code == 422
    batch_id = upload(world, {"E1_a.pdf": pdf()}, who=hr).json()["id"]
    assert publish(world, batch_id, hr).status_code == 200
    assert publish(world, batch_id, hr).status_code == 409


def test_reupload_replaces_a_draft_but_not_a_published_month(world: World) -> None:
    hr = hr_person(world)
    first = upload(world, {"E1_a.pdf": pdf("old")}, who=hr).json()
    second = upload(world, {"B1_a.pdf": pdf("new")}, who=hr).json()
    assert second["id"] == first["id"]
    assert [m["employee_code"] for m in second["matched"]] == ["B1"]
    assert publish(world, second["id"], hr).status_code == 200
    assert upload(world, {"E1_a.pdf": pdf()}, who=hr).status_code == 409


def test_owner_downloads_the_pdf_and_it_is_audited(world: World) -> None:
    hr = hr_person(world)
    batch_id = upload(world, {"E1_a.pdf": pdf("mine")}, who=hr).json()["id"]
    publish(world, batch_id, hr)
    payslip_id = mine(world, world.emp)[0]["id"]
    res = world.client.get(f"/payslips/{payslip_id}/file", headers=hdr(world.emp))
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content == pdf("mine")
    event = world.session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity == "payslip", AuditEvent.action == "view", AuditEvent.entity_id == payslip_id
        )
    ).one()
    assert event.actor_id == world.emp.id


def test_nobody_else_can_download_it_not_even_hr(world: World) -> None:
    hr = hr_person(world)
    batch_id = upload(world, {"E1_a.pdf": pdf()}, who=hr).json()["id"]
    publish(world, batch_id, hr)
    payslip_id = mine(world, world.emp)[0]["id"]
    for other in (world.boss, hr):
        res = world.client.get(f"/payslips/{payslip_id}/file", headers=hdr(other))
        assert res.status_code == 404


def test_unpublished_payslip_cannot_be_downloaded(world: World) -> None:
    hr = hr_person(world)
    upload(world, {"E1_a.pdf": pdf()}, who=hr)
    draft_id = world.session.scalars(select(Payslip.id)).first()
    assert draft_id is not None
    res = world.client.get(f"/payslips/{draft_id}/file", headers=hdr(world.emp))
    assert res.status_code == 404


def test_download_needs_sign_in(world: World) -> None:
    assert world.client.get("/payslips/1/file").status_code in (401, 403)
    assert world.client.get("/payslips/mine").status_code in (401, 403)
