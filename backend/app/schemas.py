from pydantic import BaseModel
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