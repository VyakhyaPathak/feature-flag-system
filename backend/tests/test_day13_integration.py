"""
Day 13: Milestone 2 Integration & Demo
---------------------------------------
Validates that user targeting, group targeting, percentage rollout,
environment overrides, default values, rule priority, and Redis caching
all work together correctly - the "Backend - Integration Tests &
Validation" panel of the milestone slide - plus a full end-to-end demo
walkthrough matching "3) Full Demo Walkthrough".

Priority order under test (highest -> lowest), matching
app/evaluation_engine.py's documented behavior and the task spec:
    user_whitelist > group_targeting > percentage_rollout >
    environment_override > default_value
Environment override still beats a disabled or nonexistent flag (there's
no targeting rule to compete with in that case), and still catches any
user who isn't specifically targeted - see evaluate_flag()'s docstring
for the full breakdown.

Run with: pytest test_day13_integration.py -v
"""
import pytest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app import models
from app.main import app
from app.cache import invalidate_flag_cache
from app.evaluation_engine import compute_rollout_bucket

client = TestClient(app)

FLAG_KEY = "test_day13_new_checkout"
DEV_ID, STAGING_ID, PROD_ID = 1, 2, 3  # adjust if your seeded environment IDs differ


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def cleanup(db):
    def _cleanup():
        flag_ids = [f.id for f in db.query(models.Flag).filter(models.Flag.key == FLAG_KEY).all()]
        if flag_ids:
            db.query(models.TargetingRule).filter(
                models.TargetingRule.flag_id.in_(flag_ids)
            ).delete(synchronize_session=False)
        db.query(models.Flag).filter(models.Flag.key == FLAG_KEY).delete(synchronize_session=False)
        db.query(models.FlagOverride).filter(models.FlagOverride.flag_key == FLAG_KEY).delete(synchronize_session=False)
        db.commit()
        invalidate_flag_cache(FLAG_KEY)

    _cleanup()
    yield
    _cleanup()


# ---------------------------------------------------------------------------
# 1) Rule priority order
# ---------------------------------------------------------------------------

def test_user_whitelist_beats_group_and_rollout(db, cleanup):
    flag = models.Flag(key=FLAG_KEY, environment_id=DEV_ID, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.flush()
    db.add(models.TargetingRule(flag_id=flag.id, rule_type="user_whitelist", rule_value={"user_ids": [101]}, priority=0))
    db.add(models.TargetingRule(flag_id=flag.id, rule_type="group_whitelist", rule_value={"groups": ["beta_users"]}, priority=1))
    db.add(models.TargetingRule(flag_id=flag.id, rule_type="percentage_rollout", rule_value={"percentage": 0}, priority=2))
    db.commit()

    resp = client.post("/flags/evaluate", json={
        "flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "101", "groups": ["beta_users"],
    })
    data = resp.json()
    assert resp.status_code == 200
    assert data["value"] is True
    assert data["matched_rule"] == "user_whitelisted"


def test_group_targeting_beats_rollout(db, cleanup):
    flag = models.Flag(key=FLAG_KEY, environment_id=DEV_ID, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.flush()
    db.add(models.TargetingRule(flag_id=flag.id, rule_type="group_whitelist", rule_value={"groups": ["beta_users"]}, priority=0))
    db.add(models.TargetingRule(flag_id=flag.id, rule_type="percentage_rollout", rule_value={"percentage": 0}, priority=1))
    db.commit()

    resp = client.post("/flags/evaluate", json={
        "flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "555", "groups": ["beta_users"],
    })
    data = resp.json()
    assert data["value"] is True
    assert data["matched_rule"] == "group_targeted"


def test_percentage_rollout_is_deterministic(db, cleanup):
    flag = models.Flag(key=FLAG_KEY, environment_id=DEV_ID, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.flush()
    db.add(models.TargetingRule(flag_id=flag.id, rule_type="percentage_rollout", rule_value={"percentage": 50}, priority=0))
    db.commit()

    bucket_777 = compute_rollout_bucket(777, FLAG_KEY)
    bucket_888 = compute_rollout_bucket(888, FLAG_KEY)

    r777 = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "777"}).json()
    r888 = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "888"}).json()

    assert r777["value"] == (bucket_777 < 50)
    assert r888["value"] == (bucket_888 < 50)

    # same user + same flag -> same bucket, every time
    again = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "777"}).json()
    assert again["value"] == r777["value"]


def test_environment_override_beats_everything_including_disabled_flag(db, cleanup):
    flag = models.Flag(key=FLAG_KEY, environment_id=DEV_ID, type="boolean", default_value=False, enabled=False)
    db.add(flag)
    db.flush()
    db.add(models.FlagOverride(flag_key=FLAG_KEY, environment_id=DEV_ID, enabled=True))
    db.commit()

    resp = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "999"})
    data = resp.json()
    assert data["value"] is True
    assert data["matched_rule"] == "environment_override"


def test_default_value_when_no_rules_match(db, cleanup):
    flag = models.Flag(key=FLAG_KEY, environment_id=DEV_ID, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.flush()
    db.add(models.TargetingRule(flag_id=flag.id, rule_type="percentage_rollout", rule_value={"percentage": 0}, priority=0))
    db.commit()

    resp = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "999"})
    data = resp.json()
    assert data["value"] is False
    assert data["matched_rule"] == "no_rule_matched"


# ---------------------------------------------------------------------------
# 2) Redis caching: hit on repeat request, invalidated on every write path
#    that can change a flag's resolved value.
# ---------------------------------------------------------------------------

def test_cache_hit_on_identical_repeat_request(db, cleanup):
    flag = models.Flag(key=FLAG_KEY, environment_id=DEV_ID, type="boolean", default_value=True, enabled=True)
    db.add(flag)
    db.commit()

    payload = {"flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "42"}
    first = client.post("/flags/evaluate", json=payload).json()
    second = client.post("/flags/evaluate", json=payload).json()

    assert first["source"] == "live"
    assert second["source"] == "cache"
    assert second["value"] == first["value"]


def test_cache_invalidated_after_flag_toggle(db, cleanup):
    flag = models.Flag(key=FLAG_KEY, environment_id=DEV_ID, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.commit()

    payload = {"flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "42"}
    warm = client.post("/flags/evaluate", json=payload).json()
    assert warm["source"] == "live"
    cached = client.post("/flags/evaluate", json=payload).json()
    assert cached["source"] == "cache"

    client.put(f"/flags/{flag.id}", json={"enabled": False})

    after_update = client.post("/flags/evaluate", json=payload).json()
    assert after_update["source"] == "live", (
        "Cache was NOT invalidated after a flag update - stale evaluations "
        "would be served to real traffic until the 30s TTL expires. "
        "Check that PUT /flags/{id} calls invalidate_flag_cache(flag.key)."
    )
    assert after_update["value"] == flag.default_value


def test_cache_invalidated_after_rollout_change(db, cleanup):
    flag = models.Flag(key=FLAG_KEY, environment_id=DEV_ID, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.flush()
    db.add(models.TargetingRule(flag_id=flag.id, rule_type="percentage_rollout", rule_value={"percentage": 0}, priority=0))
    db.commit()

    payload = {"flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "42"}
    client.post("/flags/evaluate", json=payload)  # warm the cache at 0%

    client.put(f"/flags/{flag.id}/rollout", json={"percentage": 100})

    after = client.post("/flags/evaluate", json=payload).json()
    assert after["source"] == "live", (
        "Cache was NOT invalidated after a rollout change. "
        "Check that PUT /flags/{id}/rollout calls invalidate_flag_cache(flag.key)."
    )
    assert after["value"] is True


def test_cache_invalidated_after_override_change(db, cleanup):
    flag = models.Flag(key=FLAG_KEY, environment_id=DEV_ID, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.commit()

    payload = {"flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "42"}
    client.post("/flags/evaluate", json=payload)  # warm the cache

    client.put(f"/flags/by-key/{FLAG_KEY}/overrides/{DEV_ID}", json={"enabled": True})

    after = client.post("/flags/evaluate", json=payload).json()
    assert after["source"] == "live", (
        "Cache was NOT invalidated after an override change. "
        "Check that PUT /flags/by-key/{key}/overrides/{env_id} calls invalidate_flag_cache(flag_key)."
    )
    assert after["value"] is True
    assert after["matched_rule"] == "environment_override"


def test_cache_invalidated_after_whitelist_change(db, cleanup):
    flag = models.Flag(key=FLAG_KEY, environment_id=DEV_ID, type="boolean", default_value=False, enabled=True)
    db.add(flag)
    db.flush()
    # A non-matching rollout rule already exists, so this isolates the
    # whitelist behavior: with ZERO rules configured, an enabled boolean
    # flag resolves to True regardless of default_value (see
    # evaluate_flag()'s "no rules configured at all" branch) - that's a
    # different code path than "a rule exists but didn't match", which is
    # what we want to exercise here.
    db.add(models.TargetingRule(flag_id=flag.id, rule_type="percentage_rollout", rule_value={"percentage": 0}, priority=0))
    db.commit()

    payload = {"flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "101"}
    warm = client.post("/flags/evaluate", json=payload).json()
    assert warm["value"] is False  # not whitelisted yet -> falls back to default

    client.post(f"/flags/{flag.id}/whitelist", json={"user_id": 101})

    after = client.post("/flags/evaluate", json=payload).json()
    assert after["source"] == "live", (
        "Cache was NOT invalidated after a whitelist change. "
        "Check that POST/DELETE /flags/{id}/whitelist calls invalidate_flag_cache(flag.key)."
    )
    assert after["value"] is True


# ---------------------------------------------------------------------------
# 3) Full demo walkthrough - mirrors the Day 13 milestone slide:
#    create -> target a group -> 50% rollout -> environment overrides ->
#    evaluate 5 different users
# ---------------------------------------------------------------------------

def test_full_demo_walkthrough_matches_milestone_slide(db, cleanup):
    # 1) Create a flag - it lives in Production, where its targeting rules
    #    (whitelist/group/rollout) will actually be evaluated. A Flag row
    #    is scoped to a single environment_id (create_flag enforces
    #    uniqueness on key + environment_id), so this flag does NOT exist
    #    in Dev or Staging as a row at all. That's fine: the environment
    #    override check in evaluate_flag() runs BEFORE the flag lookup,
    #    keyed only on flag_key + environment_id - so Dev/Staging can still
    #    be forced on via an override with no Flag row required there.
    create = client.post("/flags/", json={
        "key": FLAG_KEY, "environment_id": PROD_ID, "type": "boolean",
        "default_value": False, "enabled": True,
    })
    assert create.status_code == 200
    flag_id = create.json()["id"]

    # 2) Target a group + whitelist user_101 (so it resolves ON, per the slide)
    client.post(f"/flags/{flag_id}/groups", json={"group_name": "beta_users"})
    client.post(f"/flags/{flag_id}/whitelist", json={"user_id": 101})

    # 3) Set 50% rollout
    client.put(f"/flags/{flag_id}/rollout", json={"percentage": 50})

    # 4) Configure environment overrides - Dev & Staging forced ON.
    #    Production intentionally left un-overridden, so it falls through
    #    to whitelist -> group -> rollout -> default, matching the slide.
    client.put(f"/flags/by-key/{FLAG_KEY}/overrides/{DEV_ID}", json={"enabled": True})
    client.put(f"/flags/by-key/{FLAG_KEY}/overrides/{STAGING_ID}", json={"enabled": True})

    # 5) Test evaluation for different users, against Production
    #    (777/888/999 aren't whitelisted or grouped, so their result depends
    #    on their actual deterministic rollout bucket - compute it rather
    #    than assuming which side of 50% they land on.)
    bucket_777 = compute_rollout_bucket(777, FLAG_KEY)
    bucket_888 = compute_rollout_bucket(888, FLAG_KEY)
    bucket_999 = compute_rollout_bucket(999, FLAG_KEY)

    r101 = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": PROD_ID, "user_id": "101"}).json()
    r555 = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": PROD_ID, "user_id": "555", "groups": ["beta_users"]}).json()
    r777 = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": PROD_ID, "user_id": "777", "groups": []}).json()
    r888 = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": PROD_ID, "user_id": "888", "groups": []}).json()
    r999 = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": PROD_ID, "user_id": "999", "groups": []}).json()

    assert r101["value"] is True and r101["matched_rule"] == "user_whitelisted"
    assert r555["value"] is True and r555["matched_rule"] == "group_targeted"
    assert r777["value"] == (bucket_777 < 50)
    assert r888["value"] == (bucket_888 < 50)
    assert r999["value"] == (bucket_999 < 50)

    # Dev/Staging have overrides ON -> everyone gets True there, full stop,
    # regardless of whitelist/group/rollout state.
    dev_check = client.post("/flags/evaluate", json={"flag_key": FLAG_KEY, "environment_id": DEV_ID, "user_id": "999"}).json()
    assert dev_check["value"] is True
    assert dev_check["matched_rule"] == "environment_override"