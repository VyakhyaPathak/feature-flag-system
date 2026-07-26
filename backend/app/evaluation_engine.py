import hashlib
from sqlalchemy.orm import Session
from app import models


def _parse_user_id(user_context: dict):
    raw_user_id = user_context.get("user_id")
    if raw_user_id is None:
        return None
    try:
        return int(raw_user_id)
    except (TypeError, ValueError):
        return None


def get_user_groups(db: Session, user_id: int) -> list[str]:
    memberships = db.query(models.UserGroupMembership).filter(
        models.UserGroupMembership.user_id == str(user_id)
    ).all()
    return [m.group_name for m in memberships]


def compute_rollout_bucket(user_id, flag_key: str) -> int:
    """Deterministic SHA256-based bucket 0-99. Same user + same flag always
    produces the same bucket, on every request and every server."""
    key = f"{user_id}:{flag_key}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    return int(digest[:8], 16) % 100


# ---- Day 11: human-readable labels for the Evaluation Test Panel's
# "Priority Check" list. Order here matches the REAL evaluation order below:
# user_whitelist -> group_targeting -> percentage_rollout ->
# environment_override -> default_value, per the task spec's documented
# priority order. (A prior revision checked environment_override first/
# highest - that let a blanket environment override silently beat a
# specific user/group targeting match, which doesn't match the spec and
# isn't what you'd want from a "target these specific beta testers" rule.)
_RULE_LABELS = {
    "user_whitelist": "User Targeting",
    "group_targeting": "Group Targeting",
    "percentage_rollout": "Percentage Rollout",
    "environment_override": "Environment Override",
    "default_value": "Default Value",
}


def evaluate_flag(
    db: Session,
    flag_key: str,
    environment_id: int,
    user_context: dict = None,
    groups_override: list[str] = None,
):
    """
    Priority order (highest to lowest), matching the task spec:
        user targeting -> group targeting -> percentage rollout ->
        environment override -> default value

    Two gating states sit "above" that list because they short-circuit it
    entirely rather than competing within it:
      - Flag doesn't exist: no Flag row means no targeting rules can even
        be looked up, so user/group/percentage are all skipped. An
        environment override can still apply here (useful for forcing a
        flag on/off in an environment before the Flag row is created
        there - see the Day 13 demo, where Dev/Staging are forced on via
        override alone). Otherwise -> value=None, reason="flag_not_found".
      - Flag is disabled: a disabled flag is "off" by definition, so
        user/group/percentage targeting don't apply (there's nothing to
        target - the feature is off). An environment override is still
        checked and can force it back on (manual kill-switch/override
        pattern). Otherwise -> default_value, reason="flag_disabled".

    Once a flag exists and is enabled, the real priority order applies:
        1. User whitelist match -> True, reason="user_whitelisted"
        2. Group targeting match -> True, reason="group_targeted"
        3. Percentage rollout match -> True, reason="percentage_rollout"
        4. Environment override set -> override value, reason="environment_override"
        5. A rule existed but none matched -> default_value, reason="no_rule_matched"
        6. No rules configured at all -> True for boolean flags, reason="flag_enabled"

    Note the trade-off this implies: a targeted whitelist/group/rollout
    match now wins over a blanket environment override. An override still
    catches everyone who ISN'T specifically targeted, and still overrides
    a disabled flag - it's just no longer stronger than a specific,
    intentional targeting rule on an enabled flag.

    Day 11 additions (purely additive - "flag_key"/"value"/"reason" keys are
    unchanged, so this stays backward compatible with every Milestone 1/2
    caller and test):
    - "detail": human-readable sentence explaining the result.
    - "priority_trace": ordered list of every rule with matched/no_match/skipped,
      used to render the Priority Check sidebar.
    - groups_override: optional list[str]. When provided, group targeting is
      checked against THIS list instead of real DB group membership - lets
      the Evaluation Test Panel simulate "what if this user were in these
      groups" without writing throwaway rows into user_group_memberships.
    """
    if user_context is None:
        user_context = {}

    trace = []

    def add(rule, status, detail=None):
        trace.append({"rule": rule, "label": _RULE_LABELS[rule], "status": status, "detail": detail})

    def skip(*rules):
        for rule in rules:
            add(rule, "skipped")

    def check_override():
        return db.query(models.FlagOverride).filter(
            models.FlagOverride.flag_key == flag_key,
            models.FlagOverride.environment_id == environment_id
        ).first()

    flag = db.query(models.Flag).filter(
        models.Flag.key == flag_key,
        models.Flag.environment_id == environment_id
    ).first()

    # ---- Gate 1: flag doesn't exist at all ----
    if flag is None:
        skip("user_whitelist", "group_targeting", "percentage_rollout")
        override = check_override()
        if override is not None:
            detail = f"An environment override is set to {'ON' if override.enabled else 'OFF'} here."
            add("environment_override", "matched", detail)
            skip("default_value")
            return {
                "flag_key": flag_key, "value": override.enabled, "reason": "environment_override",
                "detail": detail, "priority_trace": trace,
            }
        add("environment_override", "no_match", "No override is set for this flag in this environment.")
        return {
            "flag_key": flag_key, "value": None, "reason": "flag_not_found",
            "detail": f"No flag found with key '{flag_key}' in this environment.",
            "priority_trace": trace,
        }

    # ---- Gate 2: flag exists but is disabled ----
    if not flag.enabled:
        skip("user_whitelist", "group_targeting", "percentage_rollout")
        override = check_override()
        if override is not None:
            detail = f"An environment override is set to {'ON' if override.enabled else 'OFF'} here, overriding the disabled flag."
            add("environment_override", "matched", detail)
            skip("default_value")
            return {
                "flag_key": flag_key, "value": override.enabled, "reason": "environment_override",
                "detail": detail, "priority_trace": trace,
            }
        add("environment_override", "no_match", "No override is set for this flag in this environment.")
        detail = "The flag is disabled, so its default value is returned regardless of any rule."
        add("default_value", "matched", detail)
        return {
            "flag_key": flag_key, "value": flag.default_value, "reason": "flag_disabled",
            "detail": detail, "priority_trace": trace,
        }

    # ---- Flag exists and is enabled: real priority order applies ----
    user_id = _parse_user_id(user_context)

    # 1. User whitelist
    whitelist_rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag.id,
        models.TargetingRule.rule_type == "user_whitelist"
    ).first()

    whitelist_matched = False
    if whitelist_rule is not None:
        whitelisted_ids = whitelist_rule.rule_value.get("user_ids", [])
        if user_id is not None and user_id in whitelisted_ids:
            whitelist_matched = True
            detail = f"User {user_id} is in this flag's user whitelist."
            add("user_whitelist", "matched", detail)
        else:
            add("user_whitelist", "no_match",
                f"User {user_id if user_id is not None else '(no user_id provided)'} "
                f"is not in this flag's whitelist.")
    else:
        add("user_whitelist", "skipped", "No user whitelist rule is configured for this flag.")

    if whitelist_matched:
        skip("group_targeting", "percentage_rollout", "environment_override", "default_value")
        return {
            "flag_key": flag_key, "value": True, "reason": "user_whitelisted",
            "detail": detail, "priority_trace": trace,
        }

    # 2. Group targeting
    group_rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag.id,
        models.TargetingRule.rule_type == "group_whitelist"
    ).first()

    group_matched = False
    if group_rule is not None:
        target_groups = group_rule.rule_value.get("groups", [])
        if groups_override is not None:
            user_groups = groups_override
        elif user_id is not None:
            user_groups = get_user_groups(db, user_id)
        else:
            user_groups = []

        matching = [g for g in target_groups if g in user_groups]
        if target_groups and matching:
            group_matched = True
            detail = f"User is in group '{matching[0]}', which is targeted by this flag."
            add("group_targeting", "matched", detail)
        else:
            add("group_targeting", "no_match", "User is not in any of this flag's targeted groups.")
    else:
        add("group_targeting", "skipped", "No group targeting rule is configured for this flag.")

    if group_matched:
        skip("percentage_rollout", "environment_override", "default_value")
        return {
            "flag_key": flag_key, "value": True, "reason": "group_targeted",
            "detail": detail, "priority_trace": trace,
        }

    # 3. Percentage rollout
    percentage_rule = db.query(models.TargetingRule).filter(
        models.TargetingRule.flag_id == flag.id,
        models.TargetingRule.rule_type == "percentage_rollout"
    ).first()

    percentage_matched = False
    if percentage_rule is not None:
        percentage = percentage_rule.rule_value.get("percentage", 0)
        if user_id is not None:
            bucket = compute_rollout_bucket(user_id, flag_key)
            if bucket < percentage:
                percentage_matched = True
                detail = f"User's bucket ({bucket}) is within the {percentage}% rollout."
                add("percentage_rollout", "matched", detail)
            else:
                add("percentage_rollout", "no_match",
                    f"User's bucket ({bucket}) is outside the {percentage}% rollout.")
        else:
            add("percentage_rollout", "no_match", "No user_id provided, so a rollout bucket can't be computed.")
    else:
        add("percentage_rollout", "skipped", "No percentage rollout rule is configured for this flag.")

    if percentage_matched:
        skip("environment_override", "default_value")
        return {
            "flag_key": flag_key, "value": True, "reason": "percentage_rollout",
            "detail": detail, "priority_trace": trace,
        }

    # 4. Environment override (checked only once nothing more specific matched)
    override = check_override()
    if override is not None:
        detail = f"An environment override is set to {'ON' if override.enabled else 'OFF'} here."
        add("environment_override", "matched", detail)
        skip("default_value")
        return {
            "flag_key": flag_key, "value": override.enabled, "reason": "environment_override",
            "detail": detail, "priority_trace": trace,
        }
    add("environment_override", "no_match", "No override is set for this flag in this environment.")

    # 5/6. Default value fallback
    if whitelist_rule is not None or group_rule is not None or percentage_rule is not None:
        detail = "A targeting rule is configured but none matched this user, so the default value is returned."
        add("default_value", "matched", detail)
        return {
            "flag_key": flag_key, "value": flag.default_value, "reason": "no_rule_matched",
            "detail": detail, "priority_trace": trace,
        }

    resolved_value = True if flag.type == "boolean" else flag.default_value
    detail = "No targeting rules are configured at all; the flag is enabled for everyone."
    add("default_value", "matched", detail)
    return {
        "flag_key": flag_key, "value": resolved_value, "reason": "flag_enabled",
        "detail": detail, "priority_trace": trace,
    }