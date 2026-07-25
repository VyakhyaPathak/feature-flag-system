import pytest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app import models
from app.main import app
from app.cache import invalidate_flag_cache

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def cleanup_test_flags(db):
    """Removes leftover test_% flags/rules/overrides, AND flushes their
    Redis cache entries - without this, a cache-eligible test (real
    user_id, no groups) could read a stale result cached by a previous
    test run within the TTL window."""
    test_keys = [
        "test_evaluate_group_flag", "test_evaluate_override_flag",
        "test_evaluate_default_flag", "test_evaluate_key_that_does_not_exist",
        "test_evaluate_anything",
    ]

    def _cleanup():
        test_flag_ids = [f.id for f in db.query(models.Flag).filter(models.Flag.key.like("test_%")).all()]
        if test_flag_ids:
            db.query(models.TargetingRule).filter(models.TargetingRule.flag_id.in_(test_flag_ids)).delete(synchronize_session=False)
        db.query(models.Flag).filter(models.Flag.key.like("test_%")).delete(synchronize_session=False)
        db.query(models.FlagOverride).filter(models.FlagOverride.flag_key.like("test_%")).delete(synchronize_session=False)
        db.commit()
        for key in test_keys:
            invalidate_flag_cache(key)

    _cleanup()
    yield
    _cleanup()


def test_evaluate_returns_group_targeted_with_simulated_groups(db, cleanup_test_flags):
    flag = models.Flag(key="test_evaluate_group_flag", environment_id=1, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.flush()
    rule = models.TargetingRule(flag_id=flag.id, rule_type="group_whitelist", rule_value={"groups": ["beta_users"]}, priority=1)
    db.add(rule)
    db.commit()

    resp = client.post("/flags/evaluate", json={
        "flag_key": "test_evaluate_group_flag", "environment_id": 1, "user_id": "101",
        "groups": ["beta_users", "premium_plan"], "context": {"plan": "premium", "country": "IN"},
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["value"] is True
    assert data["matched_rule"] == "group_targeted"
    assert "beta_users" in data["rule_detail"]
    assert len(data["priority_check"]) == 5
    assert data["source"] == "live"  # groups present -> always bypasses cache


def test_evaluate_environment_override_beats_disabled_flag(db, cleanup_test_flags):
    flag = models.Flag(key="test_evaluate_override_flag", environment_id=1, type="boolean", default_value=False, enabled=False)
    db.add(flag)
    db.flush()
    override = models.FlagOverride(flag_key="test_evaluate_override_flag", environment_id=1, enabled=True)
    db.add(override)
    db.commit()

    resp = client.post("/flags/evaluate", json={"flag_key": "test_evaluate_override_flag", "environment_id": 1})

    assert resp.status_code == 200
    data = resp.json()
    assert data["value"] is True
    assert data["matched_rule"] == "environment_override"
    trace_by_rule = {item["rule"]: item["status"] for item in data["priority_check"]}
    assert trace_by_rule["environment_override"] == "matched"
    assert trace_by_rule["default_value"] == "skipped"


def test_evaluate_falls_back_to_default_when_nothing_matches(db, cleanup_test_flags):
    flag = models.Flag(key="test_evaluate_default_flag", environment_id=1, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.flush()
    rule = models.TargetingRule(flag_id=flag.id, rule_type="user_whitelist", rule_value={"user_ids": [101]}, priority=0)
    db.add(rule)
    db.commit()

    resp = client.post("/flags/evaluate", json={"flag_key": "test_evaluate_default_flag", "environment_id": 1, "user_id": "999"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["value"] is False
    assert data["matched_rule"] == "no_rule_matched"
    trace_by_rule = {item["rule"]: item["status"] for item in data["priority_check"]}
    assert trace_by_rule["user_whitelist"] == "no_match"
    assert trace_by_rule["default_value"] == "matched"


def test_evaluate_caches_and_serves_second_call_from_cache(db, cleanup_test_flags):
    """Day 12: the exact same request (same flag_key/environment_id/user_id,
    no groups) should be 'live' on the first call and 'cache' on the second."""
    flag = models.Flag(key="test_evaluate_default_flag", environment_id=1, type="boolean", default_value=True, enabled=True)
    db.add(flag)
    db.commit()

    payload = {"flag_key": "test_evaluate_default_flag", "environment_id": 1, "user_id": "555"}
    first = client.post("/flags/evaluate", json=payload)
    second = client.post("/flags/evaluate", json=payload)

    assert first.json()["source"] == "live"
    assert second.json()["source"] == "cache"
    assert second.json()["value"] == first.json()["value"]


def test_evaluate_rejects_unknown_environment(db, cleanup_test_flags):
    resp = client.post("/flags/evaluate", json={"flag_key": "test_evaluate_anything", "environment_id": 999999})
    assert resp.status_code == 400
    assert "does not exist" in resp.json()["detail"]


def test_evaluate_flag_not_found_still_returns_200_with_reason(db, cleanup_test_flags):
    resp = client.post("/flags/evaluate", json={"flag_key": "test_evaluate_key_that_does_not_exist", "environment_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["value"] is None
    assert data["matched_rule"] == "flag_not_found"