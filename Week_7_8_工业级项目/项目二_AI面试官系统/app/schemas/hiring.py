"""招聘业务域请求与响应模型。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    """创建岗位/JD 请求。"""

    title: str = Field(min_length=2, max_length=120)
    level: str = Field(min_length=2, max_length=40)
    department: str | None = Field(default=None, max_length=120)
    jd_text: str = Field(min_length=20)
    skill_requirements: list[str] = Field(default_factory=list)
    scoring_dimensions: list[dict[str, Any]] = Field(default_factory=list)
    status: str = Field(default="active", pattern="^(draft|active|paused|closed)$")


class JobResponse(BaseModel):
    """岗位响应。"""

    id: int
    title: str
    level: str
    department: str | None
    jd_text: str
    skill_requirements: list[str]
    scoring_dimensions: list[dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CandidateProfileCreateRequest(BaseModel):
    """创建候选人档案请求。"""

    full_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    source: str = Field(default="manual", max_length=80)
    tags: list[str] = Field(default_factory=list)
    status: str = Field(default="new", pattern="^(new|invited|profile_ready|interviewing|reviewing|hired|rejected|archived)$")
    user_id: int | None = Field(default=None, gt=0)
    resume_profile_id: int | None = Field(default=None, gt=0)


class CandidateProfileResponse(BaseModel):
    """候选人档案响应。"""

    id: int
    user_id: int | None
    resume_profile_id: int | None
    full_name: str
    email: str | None
    phone: str | None
    source: str
    tags: list[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InterviewBatchCreateRequest(BaseModel):
    """创建招聘批次请求。"""

    job_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    status: str = Field(default="draft", pattern="^(draft|active|paused|completed|archived)$")
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class InterviewBatchResponse(BaseModel):
    """招聘批次响应。"""

    id: int
    job_id: int
    name: str
    description: str | None
    status: str
    starts_at: datetime | None
    ends_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InterviewInviteCreateRequest(BaseModel):
    """创建面试邀请请求。"""

    job_id: int = Field(gt=0)
    candidate_profile_id: int = Field(gt=0)
    batch_id: int | None = Field(default=None, gt=0)
    expires_at: datetime | None = None


class InterviewInviteResponse(BaseModel):
    """面试邀请响应。"""

    id: int
    invite_token: str
    job_id: int
    candidate_profile_id: int
    batch_id: int | None
    status: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime
    job_title: str | None = None
    job_level: str | None = None
    candidate_name: str | None = None
    candidate_email_masked: str | None = None

    model_config = {"from_attributes": True}


class EvaluationRubricCreateRequest(BaseModel):
    """创建评分标准版本请求。"""

    job_id: int = Field(gt=0)
    version: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    dimensions: list[dict[str, Any]] = Field(min_length=1)
    weights: dict[str, float] = Field(default_factory=dict)
    is_active: bool = True


class EvaluationRubricResponse(BaseModel):
    """评分标准版本响应。"""

    id: int
    job_id: int
    version: str
    name: str
    dimensions: list[dict[str, Any]]
    weights: dict[str, float]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ManualReviewCreateRequest(BaseModel):
    """创建人工复核请求。"""

    session_id: str = Field(min_length=1)
    recommendation: str = Field(pattern="^(strong_hire|hire|hold|no_hire)$")
    decision: str | None = Field(default=None, pattern="^(advance|reject|waitlist|needs_more_review)$")
    score_override: int | None = Field(default=None, ge=0, le=100)
    comments: str = Field(min_length=1)
    risk_flags: list[str] = Field(default_factory=list)


class ManualReviewResponse(BaseModel):
    """人工复核响应。"""

    id: int
    session_db_id: int
    reviewer_user_id: int
    recommendation: str
    decision: str | None
    score_override: int | None
    comments: str
    risk_flags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationLogResponse(BaseModel):
    """通知日志响应。"""

    id: int
    invite_id: int | None
    candidate_profile_id: int | None
    channel: str
    recipient: str
    template_key: str
    status: str
    provider_message_id: str | None
    error_message: str | None
    payload: dict[str, Any]
    created_at: datetime
    sent_at: datetime | None

    model_config = {"from_attributes": True}
