import time
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.database import get_db
from app import models, schemas
from app.evaluation_engine import evaluate_flag
from app.cache import get_cached_evaluation, set_cached_evaluation, invalidate_flag_cache, is_flag_cached
from app.deps import get_actor
from app.audit import build_flag_snapshot, summarize_diff, write_audit_log
from app.analytics import record_evaluation, get_last_evaluated

router = APIRouter(prefix="/flags", tags=["Flags"])


@router.post("/", response_model=schemas.FlagResponse)
def create_flag(flag: schemas.FlagCreate, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    environment = db.query(models.Environment).filter(
        models.Environment.id == flag.environment_id
    ).first()
    if not environment:
        raise HTTPException(status_code=400, detail=f"Environment with id {flag.environment_id} does not exist")

    existing = db.query(models.Flag).filter(
        models.Flag.key == flag.key,
        models.Flag.environment_id == flag.environment_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Flag with this key already exists in this environment")

    new_flag = models.Flag(**flag.model_dump())
    db.add(new_flag)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save flag due to a database error")
    db.refresh(new_flag)
    invalidate_flag_cache(new_flag.key)

    after = build_flag_snapshot(db, new_flag)
    write_audit_log(
        db, actor=actor, flag_id=new_flag.id, flag_key=new_flag.key,
        environment_id=new_flag.environment_id, change_type="CREATE",
        previous_state=None, new_state=after,
        details=f"Flag created with default {'ON' if new_flag.enabled else 'OFF'}",
    )
    return new_flag


@router.get("/", response_model=list[schemas.FlagResponse])
def list_flags(environment_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Flag)
    if environment_id is not None:
        query = query.filter(models.Flag.environment_id == environment_id)
    flags = query.all()

    # Day 18: batch-fetch rollout % for all these flags in one query instead
    # of N+1 - the table needs it for every row, so this has to stay cheap.
    flag_ids = [f.id for f in flags]
    rollout_by_flag_id = {}
    if flag_ids:
        rules = (
            db.query(models.TargetingRule)
            .filter(models.TargetingRule.flag_id.in_(flag_ids), models.TargetingRule.rule_type == "percentage_rollout")
            .all()
        )
        rollout_by_flag_id = {r.flag_id: r.rule_value.get("percentage") for r in rules}

    results = []
    for f in flags:
        entry = schemas.FlagResponse.model_validate(f)
        entry.rollout_percentage = rollout_by_flag_id.get(f.id)
        results.append(entry)
    return results


@router.get("/available-groups", response_model=list[str])
def list_available_groups(db: Session = Depends(get_db)):
    rows = db.query(models.UserGroupMembership.group_name).distinct().all()
    return sorted({row[0] for row in rows})


@router.get("/keys", response_model=list[str])
def list_flag_keys(db: Session = Depends(get_db)):
    rows = db.query(models.Flag.key).distinct().all()
    return sorted({row[0] for row in rows})

@router.get("/cache-status")
def get_cache_status(keys: str):
    """Given a comma-separated list of flag keys, returns which ones
    currently have a live cached evaluation - purely a display concern
    for the Flags table's Source badge."""
    flag_keys = [k.strip() for k in keys.split(",") if k.strip()]
    return {k: is_flag_cached(k) for k in flag_keys}


def _get_canonical_flag(db: Session, flag_key: str) -> models.Flag:
    flag = (
        db.query(models.Flag)
        .filter(models.Flag.key == flag_key)
        .order_by(models.Flag.id.asc())
        .first()
    )
    if not flag:
        raise HTTPException(status_code=404, detail=f"No flag found with key '{flag_key}'")
    return flag


@router.get("/by-key/{flag_key}/overrides", response_model=list[schemas.FlagOverrideEntry])
def get_flag_overrides(flag_key: str, db: Session = Depends(get_db)):
    canonical_flag = _get_canonical_flag(db, flag_key)
    environments = db.query(models.Environment).order_by(models.Environment.id).all()
    if not environments:
        raise HTTPException(status_code=404, detail="No environments configured yet")

    results = []
    for env in environments:
        override = db.query(models.FlagOverride).filter(
            models.FlagOverride.flag_key == flag_key,
            models.FlagOverride.environment_id == env.id
        ).first()
        if override:
            results.append(schemas.FlagOverrideEntry(
                environment_id=env.id, environment_name=env.name,
                overridden=True, override_enabled=override.enabled,
                default_enabled=canonical_flag.enabled,
                effective_enabled=override.enabled, updated_at=override.updated_at,
            ))
        else:
            results.append(schemas.FlagOverrideEntry(
                environment_id=env.id, environment_name=env.name,
                overridden=False, override_enabled=None,
                default_enabled=canonical_flag.enabled,
                effective_enabled=canonical_flag.enabled, updated_at=None,
            ))
    return results


@router.put("/by-key/{flag_key}/overrides/{environment_id}", response_model=schemas.FlagOverrideEntry)
def set_flag_override(flag_key: str, environment_id: int, payload: schemas.FlagOverrideSetRequest, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    canonical_flag = _get_canonical_flag(db, flag_key)
    environment = db.query(models.Environment).filter(models.Environment.id == environment_id).first()
    if not environment:
        raise HTTPException(status_code=400, detail=f"Environment with id {environment_id} does not exist")

    override = db.query(models.FlagOverride).filter(
        models.FlagOverride.flag_key == flag_key,
        models.FlagOverride.environment_id == environment_id
    ).first()
    previous_enabled = override.enabled if override is not None else None
    if override is None:
        override = models.FlagOverride(flag_key=flag_key, environment_id=environment_id, enabled=payload.enabled)
        db.add(override)
    else:
        override.enabled = payload.enabled

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update override due to a database error")
    db.refresh(override)
    invalidate_flag_cache(flag_key)

    write_audit_log(
        db, actor=actor, flag_id=canonical_flag.id, flag_key=flag_key,
        environment_id=environment_id, change_type="UPDATE",
        previous_state={"override_enabled": previous_enabled},
        new_state={"override_enabled": override.enabled},
        details=f"Environment override set to {'ENABLED' if override.enabled else 'DISABLED'} in {environment.name}",
    )
    return schemas.FlagOverrideEntry(
        environment_id=environment_id, environment_name=environment.name,
        overridden=True, override_enabled=override.enabled,
        default_enabled=canonical_flag.enabled, effective_enabled=override.enabled,
        updated_at=override.updated_at,
    )


@router.delete("/by-key/{flag_key}/overrides/{environment_id}", response_model=schemas.FlagOverrideEntry)
def clear_flag_override(flag_key: str, environment_id: int, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    canonical_flag = _get_canonical_flag(db, flag_key)
    environment = db.query(models.Environment).filter(models.Environment.id == environment_id).first()
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")

    override = db.query(models.FlagOverride).filter(
        models.FlagOverride.flag_key == flag_key,
        models.FlagOverride.environment_id == environment_id
    ).first()
    if override is None:
        raise HTTPException(status_code=404, detail="No override exists for this flag in this environment")

    previous_enabled = override.enabled
    try:
        db.delete(override)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to clear override due to a database error")
    invalidate_flag_cache(flag_key)

    write_audit_log(
        db, actor=actor, flag_id=canonical_flag.id, flag_key=flag_key,
        environment_id=environment_id, change_type="UPDATE",
        previous_state={"override_enabled": previous_enabled},
        new_state={"override_enabled": None},
        details=f"Environment override cleared in {environment.name}",
    )
    return schemas.FlagOverrideEntry(
        environment_id=environment_id, environment_name=environment.name,
        overridden=False, override_enabled=None,
        default_enabled=canonical_flag.enabled, effective_enabled=canonical_flag.enabled,
        updated_at=None,
    )


@router.get("/{flag_id}", response_model=schemas.FlagResponse)
def get_flag(flag_id: int, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    return flag


@router.put("/{flag_id}", response_model=schemas.FlagResponse)
def update_flag(flag_id: int, flag_update: schemas.FlagUpdate, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    update_data = flag_update.model_dump(exclude_unset=True)
    before = build_flag_snapshot(db, flag)
    for field, value in update_data.items():
        setattr(flag, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update flag due to a database error")
    db.refresh(flag)
    invalidate_flag_cache(flag.key)

    after = build_flag_snapshot(db, flag)
    only_enabled_changed = (
        before["enabled"] != after["enabled"]
        and before["rollout_percentage"] == after["rollout_percentage"]
        and before["target_groups"] == after["target_groups"]
        and before["whitelist_users"] == after["whitelist_users"]
    )
    if only_enabled_changed:
        change_type = "ENABLE" if after["enabled"] else "DISABLE"
        details = f"Flag {'enabled' if after['enabled'] else 'disabled'}"
    else:
        change_type = "UPDATE"
        details = summarize_diff(before, after, fallback="Flag configuration updated")
    write_audit_log(
        db, actor=actor, flag_id=flag.id, flag_key=flag.key,
        environment_id=flag.environment_id, change_type=change_type,
        previous_state=before, new_state=after, details=details,
    )
    return flag


@router.delete("/{flag_id}")
def delete_flag(flag_id: int, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    flag_key = flag.key
    environment_id = flag.environment_id
    before = build_flag_snapshot(db, flag)
    try:
        db.delete(flag)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete flag due to a database error")
    invalidate_flag_cache(flag_key)

    write_audit_log(
        db, actor=actor, flag_id=flag_id, flag_key=flag_key,
        environment_id=environment_id, change_type="DELETE",
        previous_state=before, new_state=None, details="Flag deleted",
    )
    return {"message": "Flag deleted successfully"}


# ---- Day 7: User Targeting (Whitelist) ----

@router.get("/{flag_id}/whitelist", response_model=list[int])
def get_whitelist(flag_id: int, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "user_whitelist"
    ).first()
    return rule.rule_value.get("user_ids", []) if rule else []


@router.post("/{flag_id}/whitelist", response_model=list[int])
def add_to_whitelist(flag_id: int, payload: schemas.UserIdRequest, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "user_whitelist"
    ).first()
    before = build_flag_snapshot(db, flag)
    if rule is None:
        rule = models.TargetingRule(flag_id=flag_id, rule_type="user_whitelist", rule_value={"user_ids": []}, priority=0)
        db.add(rule)
        db.flush()

    user_ids = list(rule.rule_value.get("user_ids", []))
    if payload.user_id in user_ids:
        raise HTTPException(status_code=400, detail="User ID already in whitelist")
    user_ids.append(payload.user_id)
    rule.rule_value = {"user_ids": user_ids}
    flag_modified(rule, "rule_value")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update whitelist due to a database error")
    db.refresh(rule)
    invalidate_flag_cache(flag.key)

    after = build_flag_snapshot(db, flag)
    write_audit_log(
        db, actor=actor, flag_id=flag.id, flag_key=flag.key,
        environment_id=flag.environment_id, change_type="UPDATE",
        previous_state=before, new_state=after,
        details=f"User whitelist: added user {payload.user_id}",
    )
    return rule.rule_value["user_ids"]


@router.delete("/{flag_id}/whitelist/{user_id}", response_model=list[int])
def remove_from_whitelist(flag_id: int, user_id: int, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "user_whitelist"
    ).first()
    if rule is None:
        raise HTTPException(status_code=404, detail="No whitelist exists for this flag")

    before = build_flag_snapshot(db, flag)
    user_ids = list(rule.rule_value.get("user_ids", []))
    if user_id not in user_ids:
        raise HTTPException(status_code=404, detail="User ID not found in whitelist")
    user_ids.remove(user_id)
    rule.rule_value = {"user_ids": user_ids}
    flag_modified(rule, "rule_value")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update whitelist due to a database error")
    db.refresh(rule)
    invalidate_flag_cache(flag.key)

    after = build_flag_snapshot(db, flag)
    write_audit_log(
        db, actor=actor, flag_id=flag.id, flag_key=flag.key,
        environment_id=flag.environment_id, change_type="UPDATE",
        previous_state=before, new_state=after,
        details=f"User whitelist: removed user {user_id}",
    )
    return rule.rule_value["user_ids"]


# ---- Day 8: Group Targeting ----

@router.get("/{flag_id}/groups", response_model=list[str])
def get_group_targeting(flag_id: int, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "group_whitelist"
    ).first()
    return rule.rule_value.get("groups", []) if rule else []


@router.post("/{flag_id}/groups", response_model=list[str])
def add_group_targeting(flag_id: int, payload: schemas.GroupNameRequest, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "group_whitelist"
    ).first()
    before = build_flag_snapshot(db, flag)
    if rule is None:
        rule = models.TargetingRule(flag_id=flag_id, rule_type="group_whitelist", rule_value={"groups": []}, priority=1)
        db.add(rule)
        db.flush()

    groups = list(rule.rule_value.get("groups", []))
    if payload.group_name in groups:
        raise HTTPException(status_code=400, detail="Group already selected for this flag")
    groups.append(payload.group_name)
    rule.rule_value = {"groups": groups}
    flag_modified(rule, "rule_value")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update group targeting due to a database error")
    db.refresh(rule)
    invalidate_flag_cache(flag.key)

    after = build_flag_snapshot(db, flag)
    write_audit_log(
        db, actor=actor, flag_id=flag.id, flag_key=flag.key,
        environment_id=flag.environment_id, change_type="UPDATE",
        previous_state=before, new_state=after,
        details=f"Group targeting: added '{payload.group_name}'",
    )
    return rule.rule_value["groups"]


@router.delete("/{flag_id}/groups/{group_name}", response_model=list[str])
def remove_group_targeting(flag_id: int, group_name: str, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "group_whitelist"
    ).first()
    if rule is None:
        raise HTTPException(status_code=404, detail="No group targeting rule exists for this flag")

    before = build_flag_snapshot(db, flag)
    groups = list(rule.rule_value.get("groups", []))
    if group_name not in groups:
        raise HTTPException(status_code=404, detail="Group not found in this flag's targeting rule")
    groups.remove(group_name)
    rule.rule_value = {"groups": groups}
    flag_modified(rule, "rule_value")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update group targeting due to a database error")
    db.refresh(rule)
    invalidate_flag_cache(flag.key)

    after = build_flag_snapshot(db, flag)
    write_audit_log(
        db, actor=actor, flag_id=flag.id, flag_key=flag.key,
        environment_id=flag.environment_id, change_type="UPDATE",
        previous_state=before, new_state=after,
        details=f"Group targeting: removed '{group_name}'",
    )
    return rule.rule_value["groups"]


# ---- Day 9: Percentage Rollout ----

@router.get("/{flag_id}/rollout", response_model=int)
def get_rollout_percentage(flag_id: int, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "percentage_rollout"
    ).first()
    return rule.rule_value.get("percentage", 0) if rule else 0


@router.put("/{flag_id}/rollout", response_model=int)
def set_rollout_percentage(flag_id: int, payload: schemas.RolloutPercentageRequest, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "percentage_rollout"
    ).first()
    before = build_flag_snapshot(db, flag)
    if rule is None:
        rule = models.TargetingRule(flag_id=flag_id, rule_type="percentage_rollout", rule_value={"percentage": payload.percentage}, priority=2)
        db.add(rule)
    else:
        rule.rule_value = {"percentage": payload.percentage}
        flag_modified(rule, "rule_value")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update rollout percentage due to a database error")
    db.refresh(rule)
    invalidate_flag_cache(flag.key)

    after = build_flag_snapshot(db, flag)
    write_audit_log(
        db, actor=actor, flag_id=flag.id, flag_key=flag.key,
        environment_id=flag.environment_id, change_type="UPDATE",
        previous_state=before, new_state=after,
        details=f"Rollout: {before['rollout_percentage']}% \u2192 {after['rollout_percentage']}%",
    )
    return rule.rule_value["percentage"]


# ---- Day 11 + Day 12: Evaluation Endpoint with Redis Caching ----

@router.post("/evaluate", response_model=schemas.EvaluateResponse)
def evaluate(payload: schemas.EvaluateRequest, db: Session = Depends(get_db)):
    environment = db.query(models.Environment).filter(
        models.Environment.id == payload.environment_id
    ).first()
    if not environment:
        raise HTTPException(status_code=400, detail=f"Environment with id {payload.environment_id} does not exist")

    # Day 16: count every evaluation (cache hit or live) for usage analytics.
    # Best-effort and never blocks the response - see app/analytics.py.
    record_evaluation(payload.flag_key)

    start = time.perf_counter()

    # Only cache real-traffic calls: a user_id must be present, and this
    # must not be a simulated "what if this user were in these groups" test
    # panel call (groups_override) - that result is only valid for this one
    # test, not safe to serve to other callers/users.
    cache_eligible = payload.user_id is not None and payload.groups is None
    cached = get_cached_evaluation(payload.flag_key, payload.environment_id, payload.user_id) if cache_eligible else None

    if cached is not None:
        cached["response_time_ms"] = round((time.perf_counter() - start) * 1000, 2)
        cached["source"] = "cache"
        return schemas.EvaluateResponse(**cached)

    user_context = {}
    if payload.user_id is not None:
        user_context["user_id"] = payload.user_id
    if payload.context:
        user_context["context"] = payload.context

    try:
        result = evaluate_flag(
            db, payload.flag_key, payload.environment_id,
            user_context=user_context, groups_override=payload.groups,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to evaluate flag due to an internal error")

    response = schemas.EvaluateResponse(
        flag_key=result["flag_key"],
        environment_id=environment.id,
        environment_name=environment.name,
        value=result["value"],
        reason=result["reason"],
        matched_rule=result["reason"],
        rule_detail=result.get("detail"),
        priority_check=result.get("priority_trace", []),
        evaluated_at=datetime.now(timezone.utc),
        request_summary={
            "flag_key": payload.flag_key,
            "environment": environment.name,
            "user_id": payload.user_id,
            "groups": payload.groups,
            "context": payload.context,
        },
        source="live",
        response_time_ms=round((time.perf_counter() - start) * 1000, 2),
    )

    if cache_eligible:
        set_cached_evaluation(payload.flag_key, payload.environment_id, payload.user_id, response.model_dump(mode="json"))

    return response


# ---- Day 16: Evaluation Analytics ----

@router.get("/by-key/{flag_key}/analytics", response_model=schemas.EvaluationAnalyticsResponse)
def get_evaluation_analytics(
    flag_key: str,
    days: int = Query(default=30, ge=1, le=90, description="7, 30, or 90 - any range up to 90 is accepted"),
    db: Session = Depends(get_db),
):
    _get_canonical_flag(db, flag_key)  # 404s if the flag doesn't exist

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now - timedelta(days=days)
    prev_window_start = now - timedelta(days=days * 2)

    rows = (
        db.query(models.EvaluationAnalytics)
        .filter(
            models.EvaluationAnalytics.flag_key == flag_key,
            models.EvaluationAnalytics.hour_bucket >= window_start,
        )
        .order_by(models.EvaluationAnalytics.hour_bucket.asc())
        .all()
    )
    prev_total = (
        db.query(models.EvaluationAnalytics)
        .filter(
            models.EvaluationAnalytics.flag_key == flag_key,
            models.EvaluationAnalytics.hour_bucket >= prev_window_start,
            models.EvaluationAnalytics.hour_bucket < window_start,
        )
        .with_entities(models.EvaluationAnalytics.count)
        .all()
    )
    prev_total = sum(c for (c,) in prev_total)

    daily: dict[str, int] = {}
    max_hour_count = 0
    max_hour_at = None
    for r in rows:
        day_key = r.hour_bucket.date().isoformat()
        daily[day_key] = daily.get(day_key, 0) + r.count
        if r.count > max_hour_count:
            max_hour_count = r.count
            max_hour_at = r.hour_bucket

    total = sum(daily.values())
    avg_per_day = round(total / days, 1) if days else 0.0
    change_pct = None
    if prev_total > 0:
        change_pct = round(((total - prev_total) / prev_total) * 100, 1)
    elif total > 0:
        change_pct = 100.0

    last_evaluated = get_last_evaluated(flag_key)
    if last_evaluated is None and rows:
        last_evaluated = rows[-1].hour_bucket

    points = [schemas.AnalyticsPoint(date=d, count=c) for d, c in sorted(daily.items())]

    return schemas.EvaluationAnalyticsResponse(
        flag_key=flag_key, days=days, total=total, avg_per_day=avg_per_day,
        max_per_hour=max_hour_count, max_per_hour_at=max_hour_at,
        last_evaluated=last_evaluated, change_pct=change_pct, points=points,
    )