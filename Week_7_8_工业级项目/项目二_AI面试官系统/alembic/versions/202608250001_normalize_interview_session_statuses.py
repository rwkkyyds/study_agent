"""normalize interview session statuses

Revision ID: 202608250001
Revises: 202608230002
Create Date: 2026-08-25 00:01:00
"""

from alembic import op


revision = "202608250001"
down_revision = "202608230002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE interview_sessions SET status = 'running' WHERE status IN ('questions_generated', 'follow_up_generated')")
    op.execute("UPDATE interview_sessions SET status = 'ai_reported' WHERE status = 'evaluated'")


def downgrade() -> None:
    op.execute("UPDATE interview_sessions SET status = 'evaluated' WHERE status = 'ai_reported'")
