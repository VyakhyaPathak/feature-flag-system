"""
Day 16 - Evaluation Analytics.

Every /evaluate call increments an hourly Redis counter (INCR is O(1) and
handles high QPS without ever touching Postgres on the hot path). A
once-a-day flush job (flush_analytics.py) scans those counters, aggregates
them into the `evaluation_analytics` table, and clears Redis - so Postgres
only ever sees one write per flag per hour, not one write per evaluation.
"""
from datetime import datetime, timezone

from app.redis_client import redis_client
from app import models

COUNTER_PREFIX = "flag_evalcount"
LAST_EVAL_PREFIX = "flag_last_eval"
# Safety net: if the daily flush is ever missed, counters still expire
# instead of growing forever. ~50 hours comfortably survives one missed day.
COUNTER_TTL_SECONDS = 60 * 60 * 50


def _hour_bucket_key(flag_key: str, when: datetime) -> str:
    return f"{COUNTER_PREFIX}:{flag_key}:{when.strftime('%Y-%m-%d-%H')}"


def record_evaluation(flag_key: str) -> None:
    """Called on every /evaluate request (cache hit or live). Best-effort:
    analytics must never break or slow down an actual evaluation."""
    now = datetime.now(timezone.utc)
    try:
        key = _hour_bucket_key(flag_key, now)
        redis_client.incr(key)
        redis_client.expire(key, COUNTER_TTL_SECONDS)
        redis_client.set(f"{LAST_EVAL_PREFIX}:{flag_key}", now.isoformat())
    except Exception:
        pass


def get_last_evaluated(flag_key: str) -> datetime | None:
    """Instant 'last evaluated' timestamp straight from Redis, so the
    dashboard doesn't have to wait for the next daily flush to show it."""
    try:
        raw = redis_client.get(f"{LAST_EVAL_PREFIX}:{flag_key}")
    except Exception:
        return None
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def flush_counters_to_db(db) -> int:
    """Scans every flag_evalcount:* key in Redis, aggregates into
    evaluation_analytics (one row per flag_key + hour), and deletes each
    Redis key once it's safely written. Returns the number of flag-hour
    buckets flushed. Meant to run once a day via cron / Task Scheduler
    (see flush_analytics.py) - matches the "Daily Flush Job" in the design."""
    flushed = 0
    cursor = 0
    pattern = f"{COUNTER_PREFIX}:*"
    while True:
        cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=200)
        for key in keys:
            try:
                _, flag_key, bucket_str = key.split(":", 2)
                count = int(redis_client.get(key) or 0)
                hour_bucket = datetime.strptime(bucket_str, "%Y-%m-%d-%H").replace(tzinfo=None)
            except (ValueError, TypeError):
                continue

            existing = db.query(models.EvaluationAnalytics).filter(
                models.EvaluationAnalytics.flag_key == flag_key,
                models.EvaluationAnalytics.hour_bucket == hour_bucket,
            ).first()
            if existing:
                existing.count += count
            else:
                db.add(models.EvaluationAnalytics(flag_key=flag_key, hour_bucket=hour_bucket, count=count))
            db.commit()
            redis_client.delete(key)
            flushed += 1
        if cursor == 0:
            break
    return flushed