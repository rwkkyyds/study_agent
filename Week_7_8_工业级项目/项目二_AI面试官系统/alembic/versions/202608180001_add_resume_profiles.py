"""add resume profiles

Revision ID: 202608180001
Revises: 202608170001
Create Date: 2026-08-18 00:01:00
"""

from alembic import op
import sqlalchemy as sa


revision = "202608180001"
down_revision = "202608170001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("projects", sa.JSON(), nullable=False),
        sa.Column("years_of_experience", sa.Integer(), nullable=True),
        sa.Column("target_keywords", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resume_profiles_id"), "resume_profiles", ["id"], unique=False)
    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.add_column(sa.Column("resume_profile_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_interview_sessions_resume_profile_id_resume_profiles",
            "resume_profiles",
            ["resume_profile_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.drop_constraint("fk_interview_sessions_resume_profile_id_resume_profiles", type_="foreignkey")
        batch_op.drop_column("resume_profile_id")
    op.drop_index(op.f("ix_resume_profiles_id"), table_name="resume_profiles")
    op.drop_table("resume_profiles")

