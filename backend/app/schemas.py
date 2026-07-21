from pydantic import BaseModel, field_validator
from typing import Optional, Any
from datetime import datetime


class FlagBase(BaseModel):
    key: str
    environment_id: int
    type: str = "boolean"
    default_value: Any = False
    enabled: bool = False
    description: Optional[str] = None
    owner_team: Optional[str] = None

    @field_validator("key")
    @classmethod
    def key_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Flag key cannot be empty")
        return v.strip()

    @field_validator("type")
    @classmethod
    def type_must_be_valid(cls, v):
        allowed = {"boolean", "string", "number"}
        if v not in allowed:
            raise ValueError(f"Type must be one of {allowed}")
        return v


class FlagCreate(FlagBase):
    pass


class FlagUpdate(BaseModel):
    type: Optional[str] = None
    default_value: Optional[Any] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None
    owner_team: Optional[str] = None


class FlagResponse(FlagBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserIdRequest(BaseModel):
    user_id: int

    @field_validator("user_id")
    @classmethod
    def user_id_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("user_id must be a positive integer")
        return v


class GroupNameRequest(BaseModel):
    group_name: str

    @field_validator("group_name")
    @classmethod
    def group_name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("group_name cannot be empty")
        return v.strip()


class RolloutPercentageRequest(BaseModel):
    percentage: int

    @field_validator("percentage")
    @classmethod
    def percentage_must_be_in_range(cls, v):
        if v < 0 or v > 100:
            raise ValueError("percentage must be between 0 and 100")
        return v


# ---- Day 10: Environments ----

class EnvironmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "active"

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Environment name cannot be empty")
        return v.strip()

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v):
        allowed = {"active", "inactive"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Environment name cannot be empty")
        return v.strip() if v else v

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v):
        if v is not None and v not in {"active", "inactive"}:
            raise ValueError("Status must be one of {'active', 'inactive'}")
        return v


class EnvironmentResponse(EnvironmentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Day 10: Flag Overrides by Environment ----

class FlagOverrideEntry(BaseModel):
    environment_id: int
    environment_name: str
    overridden: bool                        # True = "Overridden", False = "Using Default"
    override_enabled: Optional[bool] = None  # the raw toggle value, only set when overridden
    default_enabled: bool                    # the flag's own base enabled state (shown once at top)
    effective_enabled: bool                  # override_enabled if overridden else default_enabled
    updated_at: Optional[datetime] = None


class FlagOverrideSetRequest(BaseModel):
    enabled: bool