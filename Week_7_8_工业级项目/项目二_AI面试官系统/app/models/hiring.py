"""企业级招聘业务域模型。"""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Job(Base):
    """招聘岗位/JD。"""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
        Index("ix_jobs_created_by_user_id", "created_by_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[str] = mapped_column(String(40), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    skill_requirements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    scoring_dimensions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    batches = relationship("InterviewBatch", back_populates="job", cascade="all, delete-orphan")
    invites = relationship("InterviewInvite", back_populates="job")
    rubrics = relationship("EvaluationRubric", back_populates="job", cascade="all, delete-orphan")
    interview_sessions = relationship("InterviewSession", back_populates="job")


class CandidateProfile(Base):
    """真实招聘候选人档案，不替代简历解析画像。"""

    __tablename__ = "candidate_profiles"
    __table_args__ = (
        Index("ix_candidate_profiles_status_created_at", "status", "created_at"),
        Index("ix_candidate_profiles_email", "email"),
        Index("ix_candidate_profiles_created_by_user_id", "created_by_user_id"),
        Index("ix_candidate_profiles_user_id", "user_id"),
        Index("ix_candidate_profiles_resume_profile_id", "resume_profile_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resume_profile_id: Mapped[int | None] = mapped_column(ForeignKey("resume_profiles.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source: Mapped[str] = mapped_column(String(80), default="manual", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="new", nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    invites = relationship("InterviewInvite", back_populates="candidate_profile")
    interview_sessions = relationship("InterviewSession", back_populates="candidate_profile")
    notification_logs = relationship("NotificationLog", back_populates="candidate_profile")


class InterviewBatch(Base):
    """招聘批次。"""

    __tablename__ = "interview_batches"
    __table_args__ = (
        Index("ix_interview_batches_job_id", "job_id"),
        Index("ix_interview_batches_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    job = relationship("Job", back_populates="batches")
    invites = relationship("InterviewInvite", back_populates="batch")
    interview_sessions = relationship("InterviewSession", back_populates="interview_batch")


class InterviewInvite(Base):
    """候选人面试邀请。"""

    __tablename__ = "interview_invites"
    __table_args__ = (
        Index("ix_interview_invites_candidate_profile_id", "candidate_profile_id"),
        Index("ix_interview_invites_job_id", "job_id"),
        Index("ix_interview_invites_batch_id", "batch_id"),
        Index("ix_interview_invites_status_expires_at", "status", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invite_token: Mapped[str] = mapped_column(String(96), unique=True, index=True, nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("interview_batches.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="invited", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("Job", back_populates="invites")
    candidate_profile = relationship("CandidateProfile", back_populates="invites")
    batch = relationship("InterviewBatch", back_populates="invites")
    interview_sessions = relationship("InterviewSession", back_populates="invite")
    notification_logs = relationship("NotificationLog", back_populates="invite")

    @property
    def job_title(self) -> str | None:
        """候选人邀请落地页展示用岗位名称。"""

        return self.job.title if self.job else None

    @property
    def job_level(self) -> str | None:
        """候选人邀请落地页展示用岗位级别。"""

        return self.job.level if self.job else None

    @property
    def candidate_name(self) -> str | None:
        """候选人邀请落地页展示用姓名。"""

        return self.candidate_profile.full_name if self.candidate_profile else None

    @property
    def candidate_email_masked(self) -> str | None:
        """候选人邀请落地页展示用脱敏邮箱。"""

        if not self.candidate_profile or not self.candidate_profile.email:
            return None
        local, separator, domain = self.candidate_profile.email.partition("@")
        if not separator:
            return None
        visible = local[:2] if len(local) > 2 else local[:1]
        return f"{visible}***@{domain}"


class EvaluationRubric(Base):
    """岗位评分标准版本。"""

    __tablename__ = "evaluation_rubrics"
    __table_args__ = (
        UniqueConstraint("job_id", "version", name="uq_evaluation_rubrics_job_version"),
        Index("ix_evaluation_rubrics_job_id", "job_id"),
        Index("ix_evaluation_rubrics_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    dimensions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    weights: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("Job", back_populates="rubrics")
    interview_sessions = relationship("InterviewSession", back_populates="rubric")


class ManualReview(Base):
    """面试官/HR 人工复核意见。"""

    __tablename__ = "manual_reviews"
    __table_args__ = (
        Index("ix_manual_reviews_session_db_id", "session_db_id"),
        Index("ix_manual_reviews_reviewer_user_id", "reviewer_user_id"),
        Index("ix_manual_reviews_recommendation", "recommendation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_db_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    reviewer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(40), nullable=False)
    decision: Mapped[str | None] = mapped_column(String(40), nullable=True)
    score_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments: Mapped[str] = mapped_column(Text, nullable=False)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    session = relationship("InterviewSession", back_populates="manual_reviews")


class NotificationLog(Base):
    """通知发送日志。"""

    __tablename__ = "notification_logs"
    __table_args__ = (
        Index("ix_notification_logs_invite_id", "invite_id"),
        Index("ix_notification_logs_candidate_profile_id", "candidate_profile_id"),
        Index("ix_notification_logs_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invite_id: Mapped[int | None] = mapped_column(ForeignKey("interview_invites.id"), nullable=True)
    candidate_profile_id: Mapped[int | None] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    template_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    invite = relationship("InterviewInvite", back_populates="notification_logs")
    candidate_profile = relationship("CandidateProfile", back_populates="notification_logs")
