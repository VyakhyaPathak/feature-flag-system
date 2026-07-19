from sqlalchemy.orm import Session
from app import models


def _parse_user_id(user_context: dict):
    """Safely extracts and int-coerces user_id from user_context, or None."""
    raw_user_id = user_context.get("user_id")
    if raw_user_id is None:
        return None
    try:
        return int(raw_user_id)
    except (TypeError, ValueError):
        return None


def get_user_groups(db: Session, user_id: int) -> list[str]:
    """Returns the group names this user belongs to. user_id is stored as a
    string in user_group_memberships, so we convert for the lookup."""
    memberships = db.query(models.UserGroupMembership).filter(
        models.UserGroupMembership.user_id == str(user_id)
    ).all()
    return [m.group_name for m in memberships]


def evaluate_flag(db: Session, flag_key: str, environment_id: int, user_context: dict = None):
    """
    Resolves the value of a flag for a given environment and user context.

    Priority order:
    1. Flag doesn't exist -> return None (caller decides fallback)
    2. Flag is disabled -> return the default_value (kill switch behavior,
       always wins regardless of any targeting rule)
    3. A user_whitelist targeting rule exists on this flag and the user is
       in it -> return True ("user_whitelisted")
    4. A group_whitelist targeting rule exists on this flag and the user
       belongs to any of the selected groups -> return True ("group_targeted")
    5. A targeting rule exists (whitelist and/or group) but none of them
       matched this user -> return default_value ("no_rule_matched")
    6. No targeting rule exists at all -> return True for boolean flags
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

    user_id = _parse_user_id(user_context)

    whitelist_rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag.id,
        models.TargetingRule.rule_type == "user_whitelist"
    ).first()

    if whitelist_rule is not None:
        whitelisted_ids = whitelist_rule.rule_value.get("user_ids", [])
        if user_id is not None and user_id in whitelisted_ids:
            return {
                "flag_key": flag_key,
                "value": True,
                "reason": "user_whitelisted"
            }

    group_rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag.id,
        models.TargetingRule.rule_type == "group_whitelist"
    ).first()

    if group_rule is not None:
        target_groups = group_rule.rule_value.get("groups", [])
        if target_groups and user_id is not None:
            user_groups = get_user_groups(db, user_id)
            if any(g in target_groups for g in user_groups):
                return {
                    "flag_key": flag_key,
                    "value": True,
                    "reason": "group_targeted"
                }

    if whitelist_rule is not None or group_rule is not None:
        # At least one targeting rule exists on this flag, but nothing matched.
        return {
            "flag_key": flag_key,
            "value": flag.default_value,
            "reason": "no_rule_matched"
        }

    # Flag is enabled and no targeting rule exists at all yet (Milestone 1 behavior)
    resolved_value = True if flag.type == "boolean" else flag.default_value

    return {
        "flag_key": flag_key,
        "value": resolved_value,
        "reason": "flag_enabled"
    }