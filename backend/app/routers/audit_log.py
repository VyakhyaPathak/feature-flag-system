from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/audit-log", tags=["Audit Log"])


@router.get("/", response_model=schemas.AuditLogPage)
def list_audit_log(
    actor: str | None = Query(default=None, description="Exact actor email, or omit for all users"),
    flag_key: str | None = Query(default=None, description="Exact flag key, or omit for all flags"),
    date_from: datetime | None = Query(default=None, description="Inclusive start of range (UTC)"),
    date_to: datetime | None = Query(default=None, description="Inclusive end of range (UTC)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = (
        db.query(models.AuditLog, models.Environment.name)
        .outerjoin(models.Environment, models.AuditLog.environment_id == models.Environment.id)
    )

    if actor:
        query = query.filter(models.AuditLog.actor == actor)
    if flag_key:
        query = query.filter(models.AuditLog.flag_key == flag_key)
    if date_from:
        query = query.filter(models.AuditLog.timestamp >= date_from)
    if date_to:
        # Treat a bare date as inclusive of the whole day.
        end = date_to
        if end.time() == datetime.min.time():
            end = end + timedelta(days=1) - timedelta(microseconds=1)
        query = query.filter(models.AuditLog.timestamp <= end)

    query = query.order_by(models.AuditLog.timestamp.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for log, environment_name in rows:
        entry = schemas.AuditLogEntry.model_validate(log)
        entry.environment_name = environment_name
        items.append(entry)

    return schemas.AuditLogPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/actors", response_model=list[str])
def list_actors(db: Session = Depends(get_db)):
    """Distinct actors that have made a change - powers the 'Actor (User)' filter dropdown."""
    rows = db.query(models.AuditLog.actor).distinct().order_by(models.AuditLog.actor).all()
    return [r[0] for r in rows]


@router.get("/flags", response_model=list[str])
def list_logged_flags(db: Session = Depends(get_db)):
    """Distinct flag keys that appear in the audit log - powers the 'Flag Key' filter dropdown."""
    rows = (
        db.query(models.AuditLog.flag_key)
        .filter(models.AuditLog.flag_key.isnot(None))
        .distinct()
        .order_by(models.AuditLog.flag_key)
        .all()
    )
    return [r[0] for r in rows]