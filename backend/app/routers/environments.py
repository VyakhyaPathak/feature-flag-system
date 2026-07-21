from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/environments", tags=["Environments"])


@router.post("/", response_model=schemas.EnvironmentResponse)
def create_environment(env: schemas.EnvironmentCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Environment).filter(models.Environment.name == env.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="An environment with this name already exists")

    new_env = models.Environment(**env.model_dump())
    db.add(new_env)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create environment due to a database error")
    db.refresh(new_env)
    return new_env


@router.get("/", response_model=list[schemas.EnvironmentResponse])
def list_environments(db: Session = Depends(get_db)):
    return db.query(models.Environment).order_by(models.Environment.id).all()


@router.get("/{environment_id}", response_model=schemas.EnvironmentResponse)
def get_environment(environment_id: int, db: Session = Depends(get_db)):
    env = db.query(models.Environment).filter(models.Environment.id == environment_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    return env


@router.put("/{environment_id}", response_model=schemas.EnvironmentResponse)
def update_environment(environment_id: int, env_update: schemas.EnvironmentUpdate, db: Session = Depends(get_db)):
    env = db.query(models.Environment).filter(models.Environment.id == environment_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    update_data = env_update.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] != env.name:
        name_clash = db.query(models.Environment).filter(
            models.Environment.name == update_data["name"],
            models.Environment.id != environment_id
        ).first()
        if name_clash:
            raise HTTPException(status_code=400, detail="An environment with this name already exists")

    for field, value in update_data.items():
        setattr(env, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update environment due to a database error")
    db.refresh(env)
    return env


@router.delete("/{environment_id}")
def delete_environment(environment_id: int, db: Session = Depends(get_db)):
    env = db.query(models.Environment).filter(models.Environment.id == environment_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    flags_using_env = db.query(models.Flag).filter(models.Flag.environment_id == environment_id).count()
    if flags_using_env > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete this environment — {flags_using_env} flag(s) still reference it. "
                   f"Delete or reassign those flags first."
        )

    try:
        db.delete(env)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete environment due to a database error")
    return {"message": "Environment deleted successfully"}