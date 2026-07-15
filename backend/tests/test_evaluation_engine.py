import pytest
from app.database import SessionLocal
from app import models
from app.evaluation_engine import evaluate_flag


@pytest.fixture
def db():
    """Provides a database session for each test, and cleans up after."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def cleanup_test_flags(db):
    """Removes any leftover test flags (and their targeting rules) before and
    after each test, so tests don't interfere with each other."""
    def _cleanup():
        test_flag_ids = [
            f.id for f in db.query(models.Flag).filter(models.Flag.key.like("test_%")).all()
        ]
        if test_flag_ids:
            db.query(models.TargetingRule).filter(
                models.TargetingRule.flag_id.in_(test_flag_ids)
            ).delete(synchronize_session=False)
        db.query(models.Flag).filter(models.Flag.key.like("test_%")).delete(synchronize_session=False)
        db.commit()
    _cleanup()
    yield
    _cleanup()


def test_default_value_fallback(db, cleanup_test_flags):
    """Case 1: If the flag doesn't exist at all, return None with reason 'flag_not_found'."""
    result = evaluate_flag(db, "test_nonexistent_flag", environment_id=1)

    assert result["value"] is None
    assert result["reason"] == "flag_not_found"


def test_environment_override(db, cleanup_test_flags):
    """Case 2: The same flag key can behave differently across environments."""
    flag_dev = models.Flag(
        key="test_env_flag", environment_id=1, type="boolean",
        default_value=True, enabled=True
    )
    flag_prod = models.Flag(
        key="test_env_flag", environment_id=2, type="boolean",
        default_value=False, enabled=False
    )
    db.add_all([flag_dev, flag_prod])
    db.commit()

    result_dev = evaluate_flag(db, "test_env_flag", environment_id=1)
    result_prod = evaluate_flag(db, "test_env_flag", environment_id=2)

    # Enabled, no targeting rule configured -> old Day 4 behavior applies
    assert result_dev["value"] is True
    assert result_dev["reason"] == "flag_enabled"

    # Disabled short-circuits everything, regardless of any rule
    assert result_prod["value"] is False
    assert result_prod["reason"] == "flag_disabled"


def test_disabled_flag_returns_default(db, cleanup_test_flags):
    """Case 3: A disabled flag always returns its default_value, regardless of anything else."""
    flag = models.Flag(
        key="test_disabled_flag", environment_id=1, type="boolean",
        default_value=False, enabled=False
    )
    db.add(flag)
    db.commit()

    result = evaluate_flag(db, "test_disabled_flag", environment_id=1)

    assert result["value"] == flag.default_value
    assert result["reason"] == "flag_disabled"


def test_empty_user_context(db, cleanup_test_flags):
    """Case 4: Evaluation should work even when no user_context is provided at all."""
    flag = models.Flag(
        key="test_empty_context_flag", environment_id=1, type="boolean",
        default_value=False, enabled=True
    )
    db.add(flag)
    db.commit()

    result = evaluate_flag(db, "test_empty_context_flag", environment_id=1)

    assert result["value"] is True
    assert result["reason"] == "flag_enabled"


# ---- Day 7: User Whitelist Targeting ----

def test_whitelisted_user_gets_enabled(db, cleanup_test_flags):
    """Case 5: A user in the whitelist gets the flag enabled, even if default_value is False."""
    flag = models.Flag(
        key="test_whitelist_flag", environment_id=1, type="boolean",
        default_value=False, enabled=True
    )
    db.add(flag)
    db.flush()  # get flag.id before creating the targeting rule

    rule = models.TargetingRule(
        flag_id=flag.id, rule_type="user_whitelist",
        rule_value={"user_ids": [101]}, priority=0
    )
    db.add(rule)
    db.commit()

    result = evaluate_flag(db, "test_whitelist_flag", environment_id=1, user_context={"user_id": 101})

    assert result["value"] is True
    assert result["reason"] == "user_whitelisted"


def test_whitelisted_user_but_flag_disabled(db, cleanup_test_flags):
    """Case 6: Priority order proof - a disabled flag returns default_value
    even for a whitelisted user. Enabled-check always comes first."""
    flag = models.Flag(
        key="test_whitelist_disabled_flag", environment_id=1, type="boolean",
        default_value=False, enabled=False
    )
    db.add(flag)
    db.flush()

    rule = models.TargetingRule(
        flag_id=flag.id, rule_type="user_whitelist",
        rule_value={"user_ids": [101]}, priority=0
    )
    db.add(rule)
    db.commit()

    result = evaluate_flag(db, "test_whitelist_disabled_flag", environment_id=1, user_context={"user_id": 101})

    assert result["value"] == flag.default_value
    assert result["reason"] == "flag_disabled"


def test_non_whitelisted_user_gets_default(db, cleanup_test_flags):
    """Case 7: A user NOT in the whitelist falls back to default_value."""
    flag = models.Flag(
        key="test_non_whitelisted_flag", environment_id=1, type="boolean",
        default_value=False, enabled=True
    )
    db.add(flag)
    db.flush()

    rule = models.TargetingRule(
        flag_id=flag.id, rule_type="user_whitelist",
        rule_value={"user_ids": [101]}, priority=0
    )
    db.add(rule)
    db.commit()

    result = evaluate_flag(db, "test_non_whitelisted_flag", environment_id=1, user_context={"user_id": 999})

    assert result["value"] == flag.default_value
    assert result["reason"] == "no_rule_matched"


def test_no_whitelist_rule_at_all(db, cleanup_test_flags):
    """Case 8: Regression check - a flag with no TargetingRule row at all
    (i.e. any Milestone 1 flag) must still behave exactly as it did in
    Milestone 1, even when a user_context is passed in."""
    flag = models.Flag(
        key="test_no_whitelist_flag", environment_id=1, type="boolean",
        default_value=False, enabled=True
    )
    db.add(flag)
    db.commit()

    result = evaluate_flag(db, "test_no_whitelist_flag", environment_id=1, user_context={"user_id": 202})

    assert result["value"] is True
    assert result["reason"] == "flag_enabled"