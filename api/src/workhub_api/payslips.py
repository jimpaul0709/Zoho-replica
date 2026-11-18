"""Payslips (WH-50, WH-51): HR uploads a month of PDFs, previews the matching, then publishes.

A file is matched to an employee by the code at the start of its name:
`<EMPLOYEE_CODE>_anything.pdf` (a ZIP is opened in memory). Only the employee a payslip belongs to
can read it, and every read is audited. HR can see the matching report, never the contents.
"""

import io
import re
import zipfile
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from workhub_api.audit import record
from workhub_api.db import CurrentUser, SessionDep
from workhub_api.models import Payslip, PayslipBatch, User
from workhub_api.permissions import require_roles

router = APIRouter(prefix="/payslips", tags=["payslips"])
HRUser = Annotated[User, Depends(require_roles("hr"))]

MAX_FILE_BYTES = 10 * 1024 * 1024  # per PDF
MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # per request, after unzipping
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
NAME = re.compile(r"^([^_]+)_.+\.pdf$", re.IGNORECASE)


class Matched(BaseModel):
    employee_code: str
    name: str
    filename: str


class Unmatched(BaseModel):
    filename: str
    reason: str


class Duplicate(BaseModel):
    employee_code: str
    filenames: list[str]


class BatchOut(BaseModel):
    id: int
    month: str
    status: str
    matched: list[Matched]
    unmatched: list[Unmatched]
    duplicates: list[Duplicate]


class PayslipRow(BaseModel):
    id: int
    month: str


def _out(batch: PayslipBatch) -> BatchOut:
    return BatchOut(id=batch.id, month=batch.month, status=batch.status, **batch.match_report)


def _basename(name: str) -> str:
    return re.split(r"[\\/]", name)[-1]


def _read_all(uploads: list[UploadFile]) -> tuple[list[tuple[str, bytes]], list[dict[str, str]]]:
    """Every (name, bytes) to look at, with ZIPs opened, plus files that could not be read."""
    files: list[tuple[str, bytes]] = []
    bad: list[dict[str, str]] = []
    total = 0
    for up in uploads:
        name = _basename(up.filename or "")
        data = up.file.read()
        total += len(data)
        if not name.lower().endswith(".zip"):
            files.append((name, data))
            continue
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    total += info.file_size
                    if total > MAX_UPLOAD_BYTES:
                        raise HTTPException(413, "Upload is too large")
                    inner = _basename(info.filename)
                    if info.file_size > MAX_FILE_BYTES:
                        bad.append({"filename": inner, "reason": "File too large"})
                    else:
                        files.append((inner, z.read(info)))
        except zipfile.BadZipFile:
            bad.append({"filename": name, "reason": "Not a valid ZIP file"})
    if total > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Upload is too large")
    return files, bad


def _match(
    session: Session, files: list[tuple[str, bytes]], unmatched: list[dict[str, str]]
) -> tuple[list[dict[str, str]], list[dict[str, Any]], dict[int, tuple[str, bytes]]]:
    """Sort files into matched, duplicates and unmatched (appended to `unmatched`)."""
    by_code: dict[str, list[tuple[str, bytes]]] = {}
    for name, data in files:
        m = NAME.match(name)
        if m is None:
            unmatched.append({"filename": name, "reason": "Name must look like CODE_anything.pdf"})
        elif len(data) > MAX_FILE_BYTES:
            unmatched.append({"filename": name, "reason": "File too large"})
        elif not data.startswith(b"%PDF"):
            unmatched.append({"filename": name, "reason": "Not a PDF file"})
        else:
            by_code.setdefault(m.group(1).upper(), []).append((name, data))
    users = {
        u.employee_code.upper(): u
        for u in session.scalars(select(User).where(func.upper(User.employee_code).in_(by_code)))
    }
    matched: list[dict[str, str]] = []
    duplicates: list[dict[str, Any]] = []
    keep: dict[int, tuple[str, bytes]] = {}
    for code, items in by_code.items():
        user = users.get(code)
        if user is None:
            unmatched += [
                {"filename": n, "reason": f"No employee with code {code}"} for n, _ in items
            ]
        elif len(items) > 1:
            names = sorted(n for n, _ in items)
            duplicates.append({"employee_code": user.employee_code, "filenames": names})
        else:
            name, data = items[0]
            matched.append(
                {"employee_code": user.employee_code, "name": user.name, "filename": name}
            )
            keep[user.id] = (name, data)
    return matched, duplicates, keep


@router.post("/batches", status_code=201)
def upload_batch(
    session: SessionDep,
    hr: HRUser,
    files: list[UploadFile],
    month: Annotated[str, Form()],
) -> BatchOut:
    """Upload a month. A draft month is replaced; a published month is locked."""
    if not MONTH.match(month):
        raise HTTPException(422, "month must look like 2026-11")
    contents, unmatched = _read_all(files)
    matched, duplicates, keep = _match(session, contents, unmatched)
    report = {"matched": matched, "unmatched": unmatched, "duplicates": duplicates}
    batch = session.scalar(select(PayslipBatch).where(PayslipBatch.month == month))
    if batch is not None and batch.status == "published":
        raise HTTPException(409, f"Payslips for {month} are already published")
    if batch is None:
        batch = PayslipBatch(month=month, uploaded_by=hr.id, match_report=report)
        session.add(batch)
    else:
        batch.match_report = report
        batch.uploaded_by = hr.id
        session.execute(delete(Payslip).where(Payslip.batch_id == batch.id))
    session.flush()
    session.add_all(
        Payslip(batch_id=batch.id, user_id=uid, filename=name, content=data)
        for uid, (name, data) in keep.items()
    )
    record(
        session,
        actor_id=hr.id,
        entity="payslip_batch",
        entity_id=batch.id,
        action="upload",
        after={"month": month, "matched": len(matched), "unmatched": len(unmatched)},
    )
    session.commit()
    return _out(batch)


def _batch(session: Session, batch_id: int) -> PayslipBatch:
    batch = session.get(PayslipBatch, batch_id)
    if batch is None:
        raise HTTPException(404, "No such payslip batch")
    return batch


@router.get("/batches/{batch_id}")
def get_batch(batch_id: int, session: SessionDep, _hr: HRUser) -> BatchOut:
    return _out(_batch(session, batch_id))


@router.post("/batches/{batch_id}/publish")
def publish_batch(batch_id: int, session: SessionDep, hr: HRUser) -> BatchOut:
    batch = _batch(session, batch_id)
    if batch.status == "published":
        raise HTTPException(409, "Already published")
    count = session.scalar(select(func.count(Payslip.id)).where(Payslip.batch_id == batch.id))
    if not count:
        raise HTTPException(422, "No payslips matched; nothing to publish")
    batch.status = "published"
    record(
        session,
        actor_id=hr.id,
        entity="payslip_batch",
        entity_id=batch.id,
        action="publish",
        after={"month": batch.month, "payslips": count},
    )
    session.commit()
    return _out(batch)


@router.get("/mine")
def my_payslips(session: SessionDep, user: CurrentUser) -> list[PayslipRow]:
    rows = session.execute(
        select(Payslip.id, PayslipBatch.month)
        .join(PayslipBatch, PayslipBatch.id == Payslip.batch_id)
        .where(Payslip.user_id == user.id, PayslipBatch.status == "published")
        .order_by(PayslipBatch.month.desc())
    )
    return [PayslipRow(id=i, month=m) for i, m in rows]


@router.get("/{payslip_id}/file")
def download(payslip_id: int, session: SessionDep, user: CurrentUser) -> Response:
    """The PDF, to its owner only. Anyone else, and anything unpublished, looks like a 404."""
    row = session.execute(
        select(Payslip, PayslipBatch.month)
        .join(PayslipBatch, PayslipBatch.id == Payslip.batch_id)
        .where(
            Payslip.id == payslip_id,
            Payslip.user_id == user.id,
            PayslipBatch.status == "published",
        )
    ).first()
    if row is None:
        raise HTTPException(404, "No such payslip")
    payslip, month = row
    record(
        session,
        actor_id=user.id,
        entity="payslip",
        entity_id=payslip.id,
        action="view",
        after={"month": month},
    )
    session.commit()
    return Response(
        payslip.content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="payslip-{month}.pdf"'},
    )
