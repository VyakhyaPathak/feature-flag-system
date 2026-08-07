"""
Day 15 - Comprehensive Audit Logging.

Every flag create/update/enable/disable/delete and every targeting-rule
change (whitelist, group, rollout %, environment override) writes exactly
one row to `audit_log` with actor, timestamp, environment, and a JSON diff
of the flag's full targeting state before vs. after.

This module is intentionally the *only* place that builds snapshots or
writes audit rows, so every router stays consistent.
"""
from sqlalchemy.orm import Session
from app import models


def build_flag_snapshot(db: Session, flag: models.Flag) -> dict:
    """Full targeting snapshot for a flag: enabled state + every rule type.
    This is what gets diffed (before vs. after) for every audit log entry."""
    whitelist_rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag.id,
        models.TargetingRule.rule_type == "user_whitelist"
    ).first()
    group_rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag.id,
        models.TargetingRule.rule_type == "group_whitelist"
    ).first()
    rollout_rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag.id,
        models.TargetingRule.rule_type == "percentage_rollout"
    ).first()
    return {
        "enabled": flag.enabled,
        "rollout_percentage": rollout_rule.rule_value.get("percentage", 0) if rollout_rule else 0,
        "target_groups": list(group_rule.rule_value.get("groups", [])) if group_rule else [],
        "whitelist_users": list(whitelist_rule.rule_value.get("user_ids", [])) if whitelist_rule else [],
    }


def summarize_diff(before: dict | None, after: dict | None, fallback: str) -> str:
    """One-line human-readable summary of what changed, for the Details column."""
    if before is None or after is None:
        return fallback
    parts = []
    if before.get("enabled") != after.get("enabled"):
        parts.append("Flag enabled" if after.get("enabled") else "Flag disabled")
    if before.get("rollout_percentage") != after.get("rollout_percentage"):
        parts.append(f"Rollout: {before.get('rollout_percentage', 0)}% \u2192 {after.get('rollout_percentage', 0)}%")
    if before.get("target_groups") != after.get("target_groups"):
        parts.append(f"Groups: {before.get('target_groups', [])} \u2192 {after.get('target_groups', [])}")
    if before.get("whitelist_users") != after.get("whitelist_users"):
        parts.append(f"Whitelist: {before.get('whitelist_users', [])} \u2192 {after.get('whitelist_users', [])}")
    return "; ".join(parts) if parts else fallback


def write_audit_log(
    db: Session,
    *,
    actor: str,
    flag_id: int | None = None,
    flag_key: str | None = None,
    environment_id: int | None = None,
    change_type: str,
    previous_state=None,
    new_state=None,
    details: str,
) -> models.AuditLog:
    entry = models.AuditLog(
        actor=actor,
        flag_id=flag_id,
        flag_key=flag_key,
        environment_id=environment_id,
        change_type=change_type,
        previous_state=previous_state,
        new_state=new_state,
        details=details,
    )
    db.add(entry)
    # Audit logging must never be the reason a real change fails to save.
    # The caller has already committed its own change by this point in
    # every router - this is a best-effort second commit for the log row.
    try:
        db.commit()
    except Exception:
        db.rollback()
    return entry