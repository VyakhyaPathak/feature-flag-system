import json
from app.redis_client import redis_client

CACHE_TTL_SECONDS = 30


def _cache_key(flag_key: str, environment_id: int, user_id: str) -> str:
    return f"flag_eval:{flag_key}:env:{environment_id}:user:{user_id}"


def get_cached_evaluation(flag_key: str, environment_id: int, user_id: str):
    """Returns the cached evaluation dict, or None on a miss OR if Redis is
    unreachable - caching is a performance optimization, never a hard
    dependency, so any Redis error is treated the same as a cache miss."""
    try:
        raw = redis_client.get(_cache_key(flag_key, environment_id, user_id))
    except Exception:
        return None
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def set_cached_evaluation(flag_key: str, environment_id: int, user_id: str, payload: dict):
    try:
        redis_client.setex(
            _cache_key(flag_key, environment_id, user_id),
            CACHE_TTL_SECONDS,
            json.dumps(payload, default=str),
        )
    except Exception:
        pass


def invalidate_flag_cache(flag_key: str):
    """Deletes every cached evaluation for this flag key, across all
    environments and users, using SCAN (not KEYS) so it never blocks Redis
    on a large keyspace. Call this from every write that could change this
    flag's resolved value: flag update/delete, targeting rule changes,
    rollout changes, and environment override changes."""
    pattern = f"flag_eval:{flag_key}:*"
    try:
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass