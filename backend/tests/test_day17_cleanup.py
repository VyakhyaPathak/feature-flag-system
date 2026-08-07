import pytest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app import models
from app.main import app

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def cleanup_test_flags(db):
    """Removes leftover test_% flags/rules/candidates before and after
    each test, so scans in one test don't leak into another."""
    test_keys = [
        "test_cleanup_rolled_out", "test_cleanup_disabled", "test_cleanup_partial",
    ]

    def _cleanup():
        test_flag_ids = [f.id for f in db.query(models.Flag).filter(models.Flag.key.like("test_cleanup_%")).all()]
        if test_flag_ids:
            db.query(models.TargetingRule).filter(models.TargetingRule.flag_id.in_(test_flag_ids)).delete(synchronize_session=False)
        db.query(models.Flag).filter(models.Flag.key.like("test_cleanup_%")).delete(synchronize_session=False)
        db.query(models.FlagOverride).filter(models.FlagOverride.flag_key.like("test_cleanup_%")).delete(synchronize_session=False)
        db.query(models.CleanupCandidate).filter(models.CleanupCandidate.flag_key.in_(test_keys)).delete(synchronize_session=False)
        db.commit()

    _cleanup()
    yield
    _cleanup()


def test_fully_rolled_out_flag_is_detected(db, cleanup_test_flags):
    flag = models.Flag(key="test_cleanup_rolled_out", environment_id=1, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.flush()
    rule = models.TargetingRule(flag_id=flag.id, rule_type="percentage_rollout", rule_value={"percentage": 100}, priority=2)
    db.add(rule)
    db.commit()

    resp = client.get("/cleanup/candidates?days=0")
    assert resp.status_code == 200
    data = resp.json()
    keys = {item["flag_key"]: item for item in data["items"]}
    assert "test_cleanup_rolled_out" in keys
    assert keys["test_cleanup_rolled_out"]["status_type"] == "ROLLED_OUT"


def test_fully_disabled_flag_is_detected(db, cleanup_test_flags):
    flag = models.Flag(key="test_cleanup_disabled", environment_id=1, type="boolean", default_value=False, enabled=False)
    db.add(flag)
    db.commit()

    resp = client.get("/cleanup/candidates?days=0")
    assert resp.status_code == 200
    keys = {item["flag_key"]: item for item in resp.json()["items"]}
    assert "test_cleanup_disabled" in keys
    assert keys["test_cleanup_disabled"]["status_type"] == "DISABLED"


def test_partial_rollout_is_not_a_candidate(db, cleanup_test_flags):
    flag = models.Flag(key="test_cleanup_partial", environment_id=1, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.flush()
    rule = models.TargetingRule(flag_id=flag.id, rule_type="percentage_rollout", rule_value={"percentage": 40}, priority=2)
    db.add(rule)
    db.commit()

    resp = client.get("/cleanup/candidates?days=0&page_size=200")
    assert resp.status_code == 200
    keys = {item["flag_key"] for item in resp.json()["items"]}
    assert "test_cleanup_partial" not in keys


def test_retention_threshold_filters_out_recent_candidates(db, cleanup_test_flags):
    flag = models.Flag(key="test_cleanup_disabled", environment_id=1, type="boolean", default_value=False, enabled=False)
    db.add(flag)
    db.commit()

    # freshly changed - 0 days in state, so a 30-day threshold excludes it
    resp = client.get("/cleanup/candidates?days=30&page_size=200")
    assert resp.status_code == 200
    keys = {item["flag_key"] for item in resp.json()["items"]}
    assert "test_cleanup_disabled" not in keys

    resp = client.get("/cleanup/candidates?days=0&page_size=200")
    keys = {item["flag_key"] for item in resp.json()["items"]}
    assert "test_cleanup_disabled" in keys


def test_mark_candidate_reviewed(db, cleanup_test_flags):
    flag = models.Flag(key="test_cleanup_disabled", environment_id=1, type="boolean", default_value=False, enabled=False)
    db.add(flag)
    db.commit()

    client.get("/cleanup/candidates?days=0")  # trigger a scan so the row exists

    resp = client.put(
        "/cleanup/candidates/test_cleanup_disabled/review",
        json={"reviewed": True},
        headers={"X-Actor-Email": "tester@acme.com"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reviewed"] is True
    assert data["reviewed_by"] == "tester@acme.com"
    assert data["reviewed_at"] is not None


def test_review_unknown_flag_returns_404(cleanup_test_flags):
    resp = client.put(
        "/cleanup/candidates/test_cleanup_does_not_exist/review",
        json={"reviewed": True},
    )
    assert resp.status_code == 404
