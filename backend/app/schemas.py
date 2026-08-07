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
    rollout_percentage: Optional[int] = None  # Day 18: surfaced in the flags table so rollout is visible without an extra click

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
    overridden: bool
    override_enabled: Optional[bool] = None
    default_enabled: bool
    effective_enabled: bool
    updated_at: Optional[datetime] = None


class FlagOverrideSetRequest(BaseModel):
    enabled: bool


# ---- Day 11: Flag Evaluation Endpoint & Evaluation Test Panel ----

class EvaluateRequest(BaseModel):
    flag_key: str
    environment_id: int
    user_id: Optional[str] = None
    groups: Optional[list[str]] = None
    context: Optional[dict] = None

    @field_validator("flag_key")
    @classmethod
    def flag_key_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("flag_key cannot be empty")
        return v.strip()


class PriorityCheckItem(BaseModel):
    rule: str
    label: str
    status: str  # "matched" | "no_match" | "skipped"
    detail: Optional[str] = None


class EvaluateResponse(BaseModel):
    flag_key: str
    environment_id: int
    environment_name: str
    value: Optional[Any]
    reason: str
    matched_rule: str
    rule_detail: Optional[str] = None
    priority_check: list[PriorityCheckItem]
    evaluated_at: datetime
    request_summary: dict
    # ---- Day 12: caching visibility ----
    source: str = "live"           # "live" | "cache"
    response_time_ms: float = 0.0

    # ---- Day 14/15: Audit Log ----

class AuditLogEntry(BaseModel):
    id: int
    actor: str
    flag_id: Optional[int] = None
    flag_key: Optional[str] = None
    environment_id: Optional[int] = None
    environment_name: Optional[str] = None
    change_type: str
    previous_state: Optional[Any] = None
    new_state: Optional[Any] = None
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogPage(BaseModel):
    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int


# ---- Auth: registration, login, sessions ----

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

    @field_validator("email")
    @classmethod
    def email_must_look_like_email(cls, v):
        v = (v or "").strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Enter a valid email address")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---- Day 16: Evaluation Analytics ----

class AnalyticsPoint(BaseModel):
    date: str   # "YYYY-MM-DD" - one bar in the chart
    count: int


class EvaluationAnalyticsResponse(BaseModel):
    flag_key: str
    days: int
    total: int
    avg_per_day: float
    max_per_hour: int
    max_per_hour_at: Optional[datetime] = None
    last_evaluated: Optional[datetime] = None
    change_pct: Optional[float] = None  # vs the previous equal-length period
    points: list[AnalyticsPoint]


# ---- Day 17: Flag Cleanup Tooling ----

class CleanupEnvironmentState(BaseModel):
    environment_id: int
    environment_name: str
    enabled: bool
    rollout_percentage: int


class CleanupCandidateEntry(BaseModel):
    id: int
    flag_key: str
    status_type: str  # "ROLLED_OUT" | "DISABLED"
    since_date: datetime
    days_in_state: int
    environments: list[CleanupEnvironmentState]
    last_evaluated_at: Optional[datetime] = None
    reviewed: bool
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

    class Config:
        from_attributes = True


class CleanupCandidatesPage(BaseModel):
    items: list[CleanupCandidateEntry]
    total: int
    page: int
    page_size: int
    retention_threshold_days: int
    total_candidates: int
    fully_rolled_out_count: int
    fully_disabled_count: int
    reviewed_count: int


class CleanupReviewRequest(BaseModel):
    reviewed: bool = True


class CleanupScanResult(BaseModel):
    candidates_found: int
    scanned_at: datetime