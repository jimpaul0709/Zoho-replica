"""Write an audit_event row for every change (design rule: audit on every change).

The row joins the caller's session, so it commits or rolls back together with the change itself.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from workhub_api.models import AuditEvent, Base


def snapshot(row: Base) -> dict[str, Any]:
    """Column values of a row as JSON-safe data, for the before/after fields."""
    out: dict[str, Any] = {}
    for col in inspect(row).mapper.column_attrs:
        value = getattr(row, col.key)
        out[col.key] = value.isoformat() if isinstance(value, date | datetime) else value
    return out


def record(
    session: Session,
    *,
    actor_id: int | None,
    entity: str,
    entity_id: int | None,
    action: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        entity=entity,
        entity_id=entity_id,
        action=action,
        before=before,
        after=after,
    )
    session.add(event)
    return event
