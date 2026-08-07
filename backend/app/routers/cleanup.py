from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.cleanup import scan_and_store
from app.deps import get_actor
from app.audit import write_audit_log

router = APIRouter(prefix="/cleanup", tags=["Cleanup"])


@router.get("/candidates", response_model=schemas.CleanupCandidatesPage)
def list_cleanup_candidates(
    days: int = Query(default=30, ge=0, le=365, description="Retention threshold in days - only candidates stale longer than this are returned. 0 means show every candidate regardless of age."),
    status_type: str | None = Query(default=None, description="Filter to ROLLED_OUT or DISABLED, or omit for both"),
    reviewed: bool | None = Query(default=None, description="Filter to reviewed / not-yet-reviewed candidates"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Re-scans on every call so the panel always reflects live flag state.
    The retention threshold only changes which already-detected rows are
    shown - it doesn't change what counts as a candidate."""
    scan_and_store(db)

    all_rows = db.query(models.CleanupCandidate).all()
    fully_rolled_out_count = sum(1 for r in all_rows if r.status_type == "ROLLED_OUT")
    fully_disabled_count = sum(1 for r in all_rows if r.status_type == "DISABLED")
    reviewed_count = sum(1 for r in all_rows if r.reviewed)

    filtered = [r for r in all_rows if r.days_in_state >= days]
    if status_type:
        filtered = [r for r in filtered if r.status_type == status_type.upper()]
    if reviewed is not None:
        filtered = [r for r in filtered if r.reviewed == reviewed]

    filtered.sort(key=lambda r: r.days_in_state, reverse=True)
    total = len(filtered)
    start = (page - 1) * page_size
    page_rows = filtered[start:start + page_size]

    return schemas.CleanupCandidatesPage(
        items=[schemas.CleanupCandidateEntry.model_validate(r) for r in page_rows],
        total=total,
        page=page,
        page_size=page_size,
        retention_threshold_days=days,
        total_candidates=len(all_rows),
        fully_rolled_out_count=fully_rolled_out_count,
        fully_disabled_count=fully_disabled_count,
        reviewed_count=reviewed_count,
    )


@router.post("/scan", response_model=schemas.CleanupScanResult)
def run_cleanup_scan(db: Session = Depends(get_db)):
    """Manual trigger for the same detection job the nightly script runs -
    used by the dashboard's Refresh button and by demos."""
    count = scan_and_store(db)
    return schemas.CleanupScanResult(candidates_found=count, scanned_at=datetime.now(timezone.utc))


@router.put("/candidates/{flag_key}/review", response_model=schemas.CleanupCandidateEntry)
def mark_candidate_reviewed(
    flag_key: str,
    payload: schemas.CleanupReviewRequest,
    db: Session = Depends(get_db),
    actor: str = Depends(get_actor),
):
    row = db.query(models.CleanupCandidate).filter(models.CleanupCandidate.flag_key == flag_key).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"No cleanup candidate found for flag '{flag_key}'")

    previous_reviewed = row.reviewed
    row.reviewed = payload.reviewed
    row.reviewed_at = datetime.now(timezone.utc) if payload.reviewed else None
    row.reviewed_by = actor if payload.reviewed else None

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update review status due to a database error")
    db.refresh(row)

    write_audit_log(
        db, actor=actor, flag_key=flag_key, change_type="UPDATE",
        previous_state={"reviewed": previous_reviewed},
        new_state={"reviewed": row.reviewed},
        details=f"Cleanup candidate '{flag_key}' marked as {'reviewed' if row.reviewed else 'not reviewed'}",
    )
    return row
