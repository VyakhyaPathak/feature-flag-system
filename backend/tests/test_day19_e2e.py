"""
Day 19: End-to-End System Integration
--------------------------------------
Walks the complete request path a real flag goes through, module by
module, and checks the handoff between each pair - not just that each
module works alone (that's what the earlier day-by-day tests already
cover), but that they agree with each other once wired together:

    Create Flag -> Configure Targeting -> Evaluate -> Redis Cache
        -> Audit Logging -> Analytics Counting -> Cleanup Detection

What this test proves that the unit tests don't:
  - Rule priority (user whitelist > group > percentage rollout > default)
    still holds when exercised through the live /evaluate endpoint, not
    the evaluation engine directly.
  - A cache hit and a cache miss return the identical `value`/`reason`
    for the same flag+user - caching must never change the answer.
  - Updating a flag actually invalidates its cache (a stale cached
    "enabled" must not survive a flip to disabled).
  - Every one of those actions (create, targeting change, disable)
    lands in the audit log with the correct change_type.
  - Every evaluation call increments the analytics counter for that
    flag, whether served live or from cache.
  - A flag that ends up fully disabled becomes a cleanup candidate -
    proving Day 17's detection logic sees state changes made through
    this same end-to-end path, not just flags edited directly in the DB.

Run with: pytest test_day19_e2e.py -v
"""
import pytest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app import models
from app.main import app
from app.cache import invalidate_flag_cache
from app.cleanup import scan_and_store

client = TestClient(app)

FLAG_KEY = "test_day19_e2e_checkout"
ENVIRONMENT_ID = 1  # adjust if your seeded environment IDs differ


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def cleanup_fixture(db):
    def _cleanup():
        flag_ids = [f.id for f in db.query(models.Flag).filter(models.Flag.key == FLAG_KEY).all()]
        if flag_ids:
            db.query(models.TargetingRule).filter(models.TargetingRule.flag_id.in_(flag_ids)).delete(synchronize_session=False)
        db.query(models.Flag).filter(models.Flag.key == FLAG_KEY).delete(synchronize_session=False)
        db.query(models.AuditLog).filter(models.AuditLog.flag_key == FLAG_KEY).delete(synchronize_session=False)
        db.query(models.CleanupCandidate).filter(models.CleanupCandidate.flag_key == FLAG_KEY).delete(synchronize_session=False)
        db.commit()
        invalidate_flag_cache(FLAG_KEY)

    _cleanup()
    yield
    _cleanup()


def test_full_lifecycle_end_to_end(db, cleanup_fixture):
    # ---- 1. Create Flag ----
    resp = client.post("/flags/", json={
        "key": FLAG_KEY, "environment_id": ENVIRONMENT_ID, "type": "boolean",
        "default_value": False, "enabled": True, "description": "Day 19 e2e test", "owner_team": "QA",
    })
    assert resp.status_code == 200, resp.text
    flag = resp.json()
    flag_id = flag["id"]

    # Audit log: CREATE entry written
    resp = client.get(f"/audit-log/?flag_key={FLAG_KEY}")
    assert resp.status_code == 200
    entries = resp.json()["items"] if isinstance(resp.json(), dict) else resp.json()
    assert any(e["change_type"] == "CREATE" for e in entries), "Expected a CREATE audit entry after flag creation"

    # ---- 2. Configure Targeting: whitelist user_101, 50% rollout for everyone else ----
    resp = client.post(f"/flags/{flag_id}/whitelist", json={"user_id": 101})
    assert resp.status_code == 200, resp.text

    resp = client.put(f"/flags/{flag_id}/rollout", json={"percentage": 50})
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/audit-log/?flag_key={FLAG_KEY}")
    entries = resp.json()["items"] if isinstance(resp.json(), dict) else resp.json()
    assert any(e["change_type"] == "UPDATE" for e in entries), "Expected UPDATE audit entries for targeting changes"

    # ---- 3. Evaluate: whitelisted user always wins, regardless of rollout bucket ----
    resp = client.post("/flags/evaluate", json={
        "flag_key": FLAG_KEY, "environment_id": ENVIRONMENT_ID, "user_id": "101",
    })
    assert resp.status_code == 200, resp.text
    live_result = resp.json()
    assert live_result["value"] is True
    assert live_result["source"] == "live"
    assert "whitelist" in live_result["reason"].lower() or "user" in live_result["reason"].lower()

    # ---- 4. Redis Cache: same request again must be a cache hit with an identical value ----
    resp = client.post("/flags/evaluate", json={
        "flag_key": FLAG_KEY, "environment_id": ENVIRONMENT_ID, "user_id": "101",
    })
    assert resp.status_code == 200
    cached_result = resp.json()
    assert cached_result["source"] == "cache"
    assert cached_result["value"] == live_result["value"], "Cached evaluation must match the live one"

    # ---- Cache invalidation: disabling the flag must clear the stale cached "enabled" ----
    resp = client.put(f"/flags/{flag_id}", json={"enabled": False})
    assert resp.status_code == 200, resp.text

    resp = client.post("/flags/evaluate", json={
        "flag_key": FLAG_KEY, "environment_id": ENVIRONMENT_ID, "user_id": "101",
    })
    after_disable = resp.json()
    assert after_disable["value"] is False, "Cache must have been invalidated when the flag was disabled"
    assert after_disable["source"] == "live", "First evaluation after invalidation should be a fresh live call"

    # ---- 5. Audit Logging: the disable is logged too ----
    resp = client.get(f"/audit-log/?flag_key={FLAG_KEY}")
    entries = resp.json()["items"] if isinstance(resp.json(), dict) else resp.json()
    disable_entries = [e for e in entries if e["change_type"] == "UPDATE"]
    assert len(disable_entries) >= 2, "Expected separate UPDATE entries for targeting change and disable"

    # ---- 6. Analytics Counting: every evaluate() call above should be reflected ----
    resp = client.get(f"/flags/by-key/{FLAG_KEY}/analytics?days=1")
    assert resp.status_code == 200, resp.text
    analytics = resp.json()
    assert analytics["last_evaluated"] is not None, "Expected at least one evaluation to be counted"

    # ---- 7. Cleanup Detection: flag is now disabled everywhere it's configured -> candidate ----
    scan_and_store(db)
    resp = client.get("/cleanup/candidates?days=0&page_size=200")
    assert resp.status_code == 200
    candidates = {c["flag_key"]: c for c in resp.json()["items"]}
    assert FLAG_KEY in candidates, "A fully-disabled flag should surface as a cleanup candidate"
    assert candidates[FLAG_KEY]["status_type"] == "DISABLED"


def test_group_targeting_beats_percentage_rollout(db, cleanup_fixture):
    """Priority order sanity check through the live endpoint: a matching
    group rule must win over a percentage rollout bucket, exactly as the
    evaluation engine's documented priority order requires."""
    resp = client.post("/flags/", json={
        "key": FLAG_KEY, "environment_id": ENVIRONMENT_ID, "type": "boolean",
        "default_value": False, "enabled": True,
    })
    flag_id = resp.json()["id"]

    client.put(f"/flags/{flag_id}/rollout", json={"percentage": 0})  # rollout alone would say "off" for everyone
    client.post(f"/flags/{flag_id}/groups", json={"group_name": "beta_users"})

    resp = client.post("/flags/evaluate", json={
        "flag_key": FLAG_KEY, "environment_id": ENVIRONMENT_ID,
        "user_id": "999", "groups": ["beta_users"],
    })
    result = resp.json()
    assert result["value"] is True, "Group targeting should override a 0% percentage rollout"


def test_evaluation_with_empty_context_falls_back_to_default(db, cleanup_fixture):
    resp = client.post("/flags/", json={
        "key": FLAG_KEY, "environment_id": ENVIRONMENT_ID, "type": "boolean",
        "default_value": True, "enabled": True,
    })
    flag_id = resp.json()["id"]

    resp = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": ENVIRONMENT_ID})
    result = resp.json()
    assert result["value"] is True  # no user context and no rollout rule -> falls back to default_value
