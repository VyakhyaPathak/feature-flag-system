from sqlalchemy.orm import Session
from app import models


def evaluate_flag(db: Session, flag_key: str, environment_id: int, user_context: dict = None):
    """
    Resolves the value of a flag for a given environment and user context.

    Priority order (for Day 4, simple version):
    1. Flag doesn't exist -> return None (caller decides fallback)
    2. Flag is disabled -> return the default_value (kill switch behavior)
    3. Flag is enabled -> return True (or default_value if type isn't boolean)
    """
    if user_context is None:
        user_context = {}

    flag = db.query(models.Flag).filter(
        models.Flag.key == flag_key,
        models.Flag.environment_id == environment_id
    ).first()

    if flag is None:
        return {
            "flag_key": flag_key,
            "value": None,
            "reason": "flag_not_found"
        }

    if not flag.enabled:
        return {
            "flag_key": flag_key,
            "value": flag.default_value,
            "reason": "flag_disabled"
        }

    # Flag is enabled, and (for now) no targeting rules exist yet
    resolved_value = True if flag.type == "boolean" else flag.default_value

    return {
        "flag_key": flag_key,
        "value": resolved_value,
        "reason": "flag_enabled"
    }