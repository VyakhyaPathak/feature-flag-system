from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey, TIMESTAMP, JSON, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # e.g. "development", "production"
    description = Column(Text, nullable=True)                              # Day 10
    status = Column(String(20), nullable=False, default="active")          # Day 10: "active" | "inactive"
    created_at = Column(TIMESTAMP, server_default=func.now())

    flags = relationship("Flag", back_populates="environment")


class Flag(Base):
    __tablename__ = "flags"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, index=True)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=False, index=True)
    type = Column(String(20), nullable=False, default="boolean")
    default_value = Column(JSON, nullable=False, default=False)
    enabled = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    owner_team = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    environment = relationship("Environment", back_populates="flags")
    versions = relationship("FlagVersion", back_populates="flag", cascade="all, delete-orphan")
    targeting_rules = relationship("TargetingRule", back_populates="flag", cascade="all, delete-orphan")

class FlagVersion(Base):
    __tablename__ = "flag_versions"

    id = Column(Integer, primary_key=True, index=True)
    flag_id = Column(Integer, ForeignKey("flags.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)  # full state of the flag at this point
    created_at = Column(TIMESTAMP, server_default=func.now())

    flag = relationship("Flag", back_populates="versions")


class TargetingRule(Base):
    __tablename__ = "targeting_rules"

    id = Column(Integer, primary_key=True, index=True)
    flag_id = Column(Integer, ForeignKey("flags.id"), nullable=False)
    rule_type = Column(String(30), nullable=False)  # "user_id", "group", "percentage"
    rule_value = Column(JSON, nullable=False)  # e.g. {"percentage": 30}
    priority = Column(Integer, default=0)  # lower number = evaluated first
    created_at = Column(TIMESTAMP, server_default=func.now())

    flag = relationship("Flag", back_populates="targeting_rules")


class UserGroupMembership(Base):
    __tablename__ = "user_group_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    group_name = Column(String(100), nullable=False)  # e.g. "beta_users"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(100), nullable=False, index=True)
    # Plain integer, NOT a ForeignKey - a flag can be deleted (and its audit
    # trail is exactly what should survive that), so this column must never
    # block or cascade a flag delete. flag_key below is the durable, always-
    # readable identifier for display/filtering.
    flag_id = Column(Integer, nullable=True)
    flag_key = Column(String(100), nullable=True, index=True)          # Day 15
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=True)
    change_type = Column(String(30), nullable=False)  # "CREATE", "UPDATE", "ENABLE", "DISABLE", "DELETE"
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    details = Column(Text, nullable=True)                              # Day 15: human-readable summary
    timestamp = Column(TIMESTAMP, server_default=func.now(), index=True)


# ---- Day 16: Evaluation Analytics ----

class EvaluationAnalytics(Base):
    __tablename__ = "evaluation_analytics"

    id = Column(BigInteger, primary_key=True, index=True)
    flag_key = Column(String(100), nullable=False, index=True)
    hour_bucket = Column(TIMESTAMP, nullable=False, index=True)  # truncated to the hour, UTC
    count = Column(BigInteger, nullable=False, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("flag_key", "hour_bucket", name="uq_evaluation_analytics_flag_hour"),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=True)
    role = Column(String(30), nullable=False, default="member")  # "admin" | "member"
    created_at = Column(TIMESTAMP, server_default=func.now())


# ---- Day 10: Environment-Specific Flag Overrides ----
class FlagOverride(Base):
    __tablename__ = "flag_overrides"

    id = Column(Integer, primary_key=True, index=True)
    flag_key = Column(String(100), nullable=False, index=True)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    environment = relationship("Environment")

    __table_args__ = (
        UniqueConstraint("flag_key", "environment_id", name="uq_flag_override_key_env"),
    )


# ---- Day 17: Flag Cleanup Tooling ----

class CleanupCandidate(Base):
    """One row per flag_key that is currently fully rolled out (100% +
    enabled) or fully disabled in every environment it's configured in.
    Re-computed on every scan (see app/cleanup.py) - rows are upserted by
    flag_key so `reviewed`/`reviewed_at`/`reviewed_by` survive a re-scan,
    and rows that no longer qualify (someone changed the flag) are removed."""
    __tablename__ = "cleanup_candidates"

    id = Column(BigInteger, primary_key=True, index=True)
    flag_key = Column(String(100), nullable=False, unique=True, index=True)
    status_type = Column(String(20), nullable=False, index=True)  # "ROLLED_OUT" | "DISABLED"
    since_date = Column(TIMESTAMP, nullable=False)   # last time this flag's state changed
    days_in_state = Column(Integer, nullable=False, default=0)
    environments = Column(JSON, nullable=False, default=list)  # [{environment_id, environment_name, enabled, rollout_percentage}]
    last_evaluated_at = Column(TIMESTAMP, nullable=True)
    reviewed = Column(Boolean, nullable=False, default=False)
    reviewed_at = Column(TIMESTAMP, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())