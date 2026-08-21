"""简历解析与候选人画像模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ResumeProfile(Base):
    """候选人简历解析画像。"""

    __tablename__ = "resume_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    projects: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="resume_profiles")
    interview_sessions = relationship("InterviewSession", back_populates="resume_profile")
