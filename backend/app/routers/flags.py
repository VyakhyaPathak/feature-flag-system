from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import Optional
from app.database import get_db
from app import models, schemas
from app.evaluation_engine import evaluate_flag

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
    return new_flag


@router.get("/", response_model=list[schemas.FlagResponse])
def list_flags(environment_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Flag)
    if environment_id is not None:
        query = query.filter(models.Flag.environment_id == environment_id)
    return query.all()


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
    return flag


@router.delete("/{flag_id}")
def delete_flag(flag_id: int, db: Session = Depends(get_db)):
    flag = db.query(models.Flag).filter(models.Flag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    try:
        db.delete(flag)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete flag due to a database error")
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
        rule = models.TargetingRule(
            flag_id=flag_id,
            rule_type="user_whitelist",
            rule_value={"user_ids": []},
            priority=0
        )
        db.add(rule)
        db.flush()  # ensure rule.id exists before we mutate rule_value below

    user_ids = list(rule.rule_value.get("user_ids", []))
    if payload.user_id in user_ids:
        raise HTTPException(status_code=400, detail="User ID already in whitelist")

    user_ids.append(payload.user_id)
    rule.rule_value = {"user_ids": user_ids}
    flag_modified(rule, "rule_value")  # force SQLAlchemy to detect the JSON change

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update whitelist due to a database error")
    db.refresh(rule)
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
    flag_modified(rule, "rule_value")  # force SQLAlchemy to detect the JSON change

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update whitelist due to a database error")
    db.refresh(rule)
    return rule.rule_value["user_ids"]


@router.post("/evaluate")
def evaluate(
    flag_key: str,
    environment_id: int,
    user_context: Optional[dict] = None,
    db: Session = Depends(get_db),
):
    try:
        result = evaluate_flag(db, flag_key, environment_id, user_context)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to evaluate flag due to an internal error",
        )
    return result