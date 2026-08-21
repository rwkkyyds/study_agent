"""add interview follow ups

Revision ID: 202608190001
Revises: 202608180001
Create Date: 2026-08-19 00:01:00
"""

from alembic import op
import sqlalchemy as sa


revision = "202608190001"
down_revision = "202608180001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interview_follow_ups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_db_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(length=32), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("follow_up_questions", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("workflow_trace", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_db_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("interview_follow_ups")
