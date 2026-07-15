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