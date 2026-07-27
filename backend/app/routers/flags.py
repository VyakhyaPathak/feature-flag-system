import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.database import get_db
from app import models, schemas
from app.evaluation_engine import evaluate_flag
from app.cache import get_cached_evaluation, set_cached_evaluation, invalidate_flag_cache, is_flag_cached

router = APIRouter(prefix="/flags", tags=["Flags"])


@router.post("/", response_model=schemas.FlagResponse)
def create_flag(flag: schemas.FlagCreate, db: Session = Depends(get_db)):
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
    return new_flag


@router.get("/", response_model=list[schemas.FlagResponse])
def list_flags(environment_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Flag)
    if environment_id is not None:
        query = query.filter(models.Flag.environment_id == environment_id)
    return query.all()


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
def set_flag_override(flag_key: str, environment_id: int, payload: schemas.FlagOverrideSetRequest, db: Session = Depends(get_db)):
    canonical_flag = _get_canonical_flag(db, flag_key)
    environment = db.query(models.Environment).filter(models.Environment.id == environment_id).first()
    if not environment:
        raise HTTPException(status_code=400, detail=f"Environment with id {environment_id} does not exist")

    override = db.query(models.FlagOverride).filter(
        models.FlagOverride.flag_key == flag_key,
        models.FlagOverride.environment_id == environment_id
    ).first()
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

    return schemas.FlagOverrideEntry(
        environment_id=environment_id, environment_name=environment.name,
        overridden=True, override_enabled=override.enabled,
        default_enabled=canonical_flag.enabled, effective_enabled=override.enabled,
        updated_at=override.updated_at,
    )


@router.delete("/by-key/{flag_key}/overrides/{environment_id}", response_model=schemas.FlagOverrideEntry)
def clear_flag_override(flag_key: str, environment_id: int, db: Session = Depends(get_db)):
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

    try:
        db.delete(override)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to clear override due to a database error")
    invalidate_flag_cache(flag_key)

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
def update_flag(flag_id: int, flag_update: schemas.FlagUpdate, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    update_data = flag_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(flag, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update flag due to a database error")
    db.refresh(flag)
    invalidate_flag_cache(flag.key)
    return flag


@router.delete("/{flag_id}")
def delete_flag(flag_id: int, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    flag_key = flag.key
    try:
        db.delete(flag)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete flag due to a database error")
    invalidate_flag_cache(flag_key)
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
def add_to_whitelist(flag_id: int, payload: schemas.UserIdRequest, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "user_whitelist"
    ).first()
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
    return rule.rule_value["user_ids"]


@router.delete("/{flag_id}/whitelist/{user_id}", response_model=list[int])
def remove_from_whitelist(flag_id: int, user_id: int, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "user_whitelist"
    ).first()
    if rule is None:
        raise HTTPException(status_code=404, detail="No whitelist exists for this flag")

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
def add_group_targeting(flag_id: int, payload: schemas.GroupNameRequest, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "group_whitelist"
    ).first()
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
    return rule.rule_value["groups"]


@router.delete("/{flag_id}/groups/{group_name}", response_model=list[str])
def remove_group_targeting(flag_id: int, group_name: str, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "group_whitelist"
    ).first()
    if rule is None:
        raise HTTPException(status_code=404, detail="No group targeting rule exists for this flag")

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
def set_rollout_percentage(flag_id: int, payload: schemas.RolloutPercentageRequest, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag_id,
        models.TargetingRule.rule_type == "percentage_rollout"
    ).first()
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
    return rule.rule_value["percentage"]


# ---- Day 11 + Day 12: Evaluation Endpoint with Redis Caching ----

@router.post("/evaluate", response_model=schemas.EvaluateResponse)
def evaluate(payload: schemas.EvaluateRequest, db: Session = Depends(get_db)):
    environment = db.query(models.Environment).filter(
        models.Environment.id == payload.environment_id
    ).first()
    if not environment:
        raise HTTPException(status_code=400, detail=f"Environment with id {payload.environment_id} does not exist")

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