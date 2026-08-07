from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import decode_access_token
from app import models


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> "models.User | None":
    """Resolves the signed-in user from a 'Authorization: Bearer <token>'
    header. Returns None (never raises) if there's no token or it's
    invalid/expired - callers decide whether that's acceptable."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload:
        return None
    user = db.query(models.User).filter(models.User.id == payload.get("user_id")).first()
    return user


def get_current_user(
    user: "models.User | None" = Depends(get_current_user_optional),
) -> "models.User":
    """Same as above, but requires a valid session - use on routes that
    must be logged in (e.g. GET /auth/me)."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_actor(
    user: "models.User | None" = Depends(get_current_user_optional),
    x_actor_email: str | None = Header(default=None),
) -> str:
    """Resolves 'who made this change' for the audit log.

    Preference order:
    1. The signed-in user's email, from a valid JWT (real auth, once the
       dashboard's login page is in use).
    2. An X-Actor-Email header, for callers/tests that don't go through
       the login flow.
    3. A fixed demo actor, so a write is never silently unattributed.
    """
    if user is not None:
        return user.email
    return x_actor_email or "admin@acme.com"
