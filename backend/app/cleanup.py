"""
Day 17 - Flag Cleanup Tooling & Cleanup Suggestions.

Finds flags that have settled into one of two "safe to remove" states in
every environment they're configured in, and have stayed there for a
while:

  - Fully Rolled Out: enabled with a 100% rollout everywhere -> the flag
    check can be deleted and the "on" code path hard-coded in.
  - Fully Disabled: disabled everywhere -> the flag check (and the dead
    "off" code path) can be deleted.

Flags that are mixed across environments, mid-rollout, or targeted at a
specific whitelist/group are left alone - those are still being actively
managed and are not cleanup candidates.

Detection runs through scan_and_store() below, which is the single place
that decides candidacy and writes to `cleanup_candidates`. It's called
both by GET /cleanup/candidates (so the dashboard always shows live data)
and by the standalone nightly job (run_cleanup_scan.py), so there's never
a second copy of the rules to keep in sync.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app import models
from app.analytics import get_last_evaluated

ROLLED_OUT = "ROLLED_OUT"
DISABLED = "DISABLED"


def _effective_env_state(flag, override_by_key, rollout_by_flag_id):
    """Returns (enabled, rollout_percentage) for one Flag row, folding in
    any environment override and percentage-rollout targeting rule.
    A flag with no rollout rule is treated as 100% when enabled (a plain
    on/off flag) and 0% when disabled - there's no partial state to speak
    of without a rollout rule."""
    override = override_by_key.get((flag.key, flag.environment_id))
    enabled = override.enabled if override is not None else flag.enabled
    rule = rollout_by_flag_id.get(flag.id)
    rollout = rule.rule_value.get("percentage", 0) if rule is not None else (100 if enabled else 0)
    return enabled, rollout


def scan_candidates(db: Session) -> list[dict]:
    """Evaluates every distinct flag_key across the environments it's
    configured in and returns the ones that are fully rolled out or fully
    disabled everywhere, along with the per-environment state that led to
    that verdict."""
    flags = db.query(models.Flag).all()
    environments = {e.id: e for e in db.query(models.Environment).all()}
    override_by_key = {(o.flag_key, o.environment_id): o for o in db.query(models.FlagOverride).all()}
    rollout_by_flag_id = {
        r.flag_id: r
        for r in db.query(models.TargetingRule).filter(models.TargetingRule.rule_type == "percentage_rollout").all()
    }

    by_key: dict[str, list[models.Flag]] = {}
    for f in flags:
        by_key.setdefault(f.key, []).append(f)

    now = datetime.utcnow()
    results = []
    for flag_key, rows in by_key.items():
        env_states = []
        all_rolled_out = True
        all_disabled = True
        latest_change = None

        for row in rows:
            enabled, rollout = _effective_env_state(row, override_by_key, rollout_by_flag_id)
            env = environments.get(row.environment_id)
            env_states.append({
                "environment_id": row.environment_id,
                "environment_name": env.name if env else "unknown",
                "enabled": enabled,
                "rollout_percentage": rollout,
            })
            if not (enabled and rollout >= 100):
                all_rolled_out = False
            if enabled:
                all_disabled = False

            # "since" = the most recent moment anything about this flag's
            # state changed in this environment - the flag row itself, its
            # override, or its rollout rule.
            for ts in (
                row.updated_at,
                (override_by_key.get((flag_key, row.environment_id)) or None) and override_by_key[(flag_key, row.environment_id)].updated_at,
                (rollout_by_flag_id.get(row.id) or None) and rollout_by_flag_id[row.id].created_at,
            ):
                if ts is not None and (latest_change is None or ts > latest_change):
                    latest_change = ts

        if not env_states:
            continue

        if all_rolled_out:
            status_type = ROLLED_OUT
        elif all_disabled:
            status_type = DISABLED
        else:
            continue  # mixed state - actively managed, not a candidate

        since_date = latest_change or now
        days_in_state = max((now - since_date).days, 0)

        results.append({
            "flag_key": flag_key,
            "status_type": status_type,
            "since_date": since_date,
            "days_in_state": days_in_state,
            "environments": env_states,
            "last_evaluated_at": get_last_evaluated(flag_key),
        })
    return results


def scan_and_store(db: Session) -> int:
    """Runs scan_candidates() and upserts each result into
    cleanup_candidates by flag_key, preserving any existing reviewed /
    reviewed_at / reviewed_by so a re-scan never wipes out a review.
    Flags that no longer qualify (someone changed them) drop off the
    table. Returns the number of candidates currently detected."""
    detected = scan_candidates(db)
    detected_by_key = {d["flag_key"]: d for d in detected}

    existing = {c.flag_key: c for c in db.query(models.CleanupCandidate).all()}

    for key, d in detected_by_key.items():
        row = existing.get(key)
        if row is None:
            row = models.CleanupCandidate(flag_key=key)
            db.add(row)
        row.status_type = d["status_type"]
        row.since_date = d["since_date"]
        row.days_in_state = d["days_in_state"]
        row.environments = d["environments"]
        row.last_evaluated_at = d["last_evaluated_at"]
        flag_modified(row, "environments")

    for key, row in existing.items():
        if key not in detected_by_key:
            db.delete(row)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(detected)