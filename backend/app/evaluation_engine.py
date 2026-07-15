from sqlalchemy.orm import Session
from app import models


def evaluate_flag(db: Session, flag_key: str, environment_id: int, user_context: dict = None):
    """
    Resolves the value of a flag for a given environment and user context.

    Priority order:
    1. Flag doesn't exist -> return None (caller decides fallback)
    2. Flag is disabled -> return the default_value (kill switch behavior)
    3. A user_whitelist targeting rule exists on this flag:
         - user is in the whitelist -> return True
         - user is not in the whitelist -> return default_value
    4. No targeting rule exists at all -> return True for boolean flags
       (Day 4 behavior: enabled with no rules means everyone sees it)
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

    whitelist_rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag.id,
        models.TargetingRule.rule_type == "user_whitelist"
    ).first()

    if whitelist_rule is not None:
        whitelisted_ids = whitelist_rule.rule_value.get("user_ids", [])

        raw_user_id = user_context.get("user_id")
        user_id = None
        if raw_user_id is not None:
            try:
                user_id = int(raw_user_id)
            except (TypeError, ValueError):
                user_id = None

        if user_id is not None and user_id in whitelisted_ids:
            return {
                "flag_key": flag_key,
                "value": True,
                "reason": "user_whitelisted"
            }
        else:
            return {
                "flag_key": flag_key,
                "value": flag.default_value,
                "reason": "no_rule_matched"
            }

    # Flag is enabled and no targeting rule exists yet
    resolved_value = True if flag.type == "boolean" else flag.default_value

    return {
        "flag_key": flag_key,
        "value": resolved_value,
        "reason": "flag_enabled"
    }