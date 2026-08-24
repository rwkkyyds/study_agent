"""面试业务模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class InterviewSession(Base):
    """一次模拟面试会话。"""

    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    resume_profile_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("resume_profiles.id"), nullable=True)
    job_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=True)
    candidate_profile_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("candidate_profiles.id"), nullable=True)
    interview_batch_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("interview_batches.id"), nullable=True)
    invite_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("interview_invites.id"), nullable=True)
    rubric_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("evaluation_rubrics.id"), nullable=True)
    resume_text: Mapped[str] = mapped_column(Text, nullable=False)
    job_title: Mapped[str] = mapped_column(String(120), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    candidate_summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="running", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="interview_sessions")
    resume_profile = relationship("ResumeProfile", back_populates="interview_sessions")
    job = relationship("Job", back_populates="interview_sessions")
    candidate_profile = relationship("CandidateProfile", back_populates="interview_sessions")
    interview_batch = relationship("InterviewBatch", back_populates="interview_sessions")
    invite = relationship("InterviewInvite", back_populates="interview_sessions")
    rubric = relationship("EvaluationRubric", back_populates="interview_sessions")
    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")
    answers = relationship("InterviewAnswer", back_populates="session", cascade="all, delete-orphan")
    follow_ups = relationship("InterviewFollowUp", back_populates="session", cascade="all, delete-orphan")
    report = relationship("InterviewReport", back_populates="session", uselist=False, cascade="all, delete-orphan")
    manual_reviews = relationship("ManualReview", back_populates="session", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    """一次面试中的题目快照。"""

    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_db_id: Mapped[int] = mapped_column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[str] = mapped_column(String(32), nullable=False)
    question_type: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_points: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="questions")


class InterviewAnswer(Base):
    """候选人的单题回答。"""

    __tablename__ = "interview_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_db_id: Mapped[int] = mapped_column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[str] = mapped_column(String(32), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="answers")


class InterviewFollowUp(Base):
    """多轮追问快照。"""

    __tablename__ = "interview_follow_ups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_db_id: Mapped[int] = mapped_column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[str] = mapped_column(String(32), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up_questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_trace: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="follow_ups")


class InterviewReport(Base):
    """面试评分报告。"""

    __tablename__ = "interview_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_db_id: Mapped[int] = mapped_column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(30), nullable=False)
    dimensions: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    risks: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    follow_up_questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    learning_suggestions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="report")
