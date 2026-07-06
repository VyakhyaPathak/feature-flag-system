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
    """Removes any leftover test flags before and after each test, so tests don't interfere with each other."""
    def _cleanup():
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
        default_value=False, enabled=True
    )
    flag_prod = models.Flag(
        key="test_env_flag", environment_id=2, type="boolean",
        default_value=False, enabled=False
    )
    db.add_all([flag_dev, flag_prod])
    db.commit()

    result_dev = evaluate_flag(db, "test_env_flag", environment_id=1)
    result_prod = evaluate_flag(db, "test_env_flag", environment_id=2)

    assert result_dev["value"] is True
    assert result_dev["reason"] == "flag_enabled"

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