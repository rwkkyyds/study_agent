"""initial auth and interview persistence

Revision ID: 202608170001
Revises:
Create Date: 2026-08-17 00:01:00
"""

from alembic import op
import sqlalchemy as sa


revision = "202608170001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("resume_text", sa.Text(), nullable=False),
        sa.Column("job_title", sa.String(length=120), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("candidate_summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(op.f("ix_interview_sessions_id"), "interview_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_interview_sessions_session_id"), "interview_sessions", ["session_id"], unique=False)

    op.create_table(
        "interview_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_db_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(length=32), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_db_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_db_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(length=32), nullable=False),
        sa.Column("question_type", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_points", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_db_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "interview_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_db_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=30), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("follow_up_questions", sa.JSON(), nullable=False),
        sa.Column("learning_suggestions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_db_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_db_id"),
    )


def downgrade() -> None:
    op.drop_table("interview_reports")
    op.drop_table("interview_questions")
    op.drop_table("interview_answers")
    op.drop_index(op.f("ix_interview_sessions_session_id"), table_name="interview_sessions")
    op.drop_index(op.f("ix_interview_sessions_id"), table_name="interview_sessions")
    op.drop_table("interview_sessions")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
