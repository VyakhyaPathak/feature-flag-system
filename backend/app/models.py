from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # e.g. "development", "production"
    created_at = Column(TIMESTAMP, server_default=func.now())

    flags = relationship("Flag", back_populates="environment")


class Flag(Base):
    __tablename__ = "flags"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, index=True)  # e.g. "ai_photo_editor"
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=False, index=True)
    type = Column(String(20), nullable=False, default="boolean")  # boolean, string, number
    default_value = Column(JSON, nullable=False, default=False)
    enabled = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    owner_team = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    environment = relationship("Environment", back_populates="flags")
    versions = relationship("FlagVersion", back_populates="flag")
    targeting_rules = relationship("TargetingRule", back_populates="flag")


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
    actor = Column(String(100), nullable=False)
    flag_id = Column(Integer, ForeignKey("flags.id"), nullable=True)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=True)
    change_type = Column(String(30), nullable=False)  # "created", "updated", "enabled", etc.
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    timestamp = Column(TIMESTAMP, server_default=func.now())