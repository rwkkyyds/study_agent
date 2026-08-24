"""hiring domain models

Revision ID: 202608230002
Revises: 202608230001
Create Date: 2026-08-23 00:02:00
"""

from alembic import op
import sqlalchemy as sa


revision = "202608230002"
down_revision = "202608230001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("level", sa.String(length=40), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=True),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("skill_requirements", sa.JSON(), nullable=False),
        sa.Column("scoring_dimensions", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_id"), "jobs", ["id"], unique=False)
    op.create_index("ix_jobs_created_by_user_id", "jobs", ["created_by_user_id"], unique=False)
    op.create_index("ix_jobs_status_created_at", "jobs", ["status", "created_at"], unique=False)

    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("resume_profile_id", sa.Integer(), nullable=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["resume_profile_id"], ["resume_profiles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_candidate_profiles_id"), "candidate_profiles", ["id"], unique=False)
    op.create_index("ix_candidate_profiles_created_by_user_id", "candidate_profiles", ["created_by_user_id"], unique=False)
    op.create_index("ix_candidate_profiles_email", "candidate_profiles", ["email"], unique=False)
    op.create_index("ix_candidate_profiles_resume_profile_id", "candidate_profiles", ["resume_profile_id"], unique=False)
    op.create_index("ix_candidate_profiles_status_created_at", "candidate_profiles", ["status", "created_at"], unique=False)
    op.create_index("ix_candidate_profiles_user_id", "candidate_profiles", ["user_id"], unique=False)

    op.create_table(
        "interview_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interview_batches_id"), "interview_batches", ["id"], unique=False)
    op.create_index("ix_interview_batches_job_id", "interview_batches", ["job_id"], unique=False)
    op.create_index("ix_interview_batches_status_created_at", "interview_batches", ["status", "created_at"], unique=False)

    op.create_table(
        "evaluation_rubrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "version", name="uq_evaluation_rubrics_job_version"),
    )
    op.create_index(op.f("ix_evaluation_rubrics_id"), "evaluation_rubrics", ["id"], unique=False)
    op.create_index("ix_evaluation_rubrics_is_active", "evaluation_rubrics", ["is_active"], unique=False)
    op.create_index("ix_evaluation_rubrics_job_id", "evaluation_rubrics", ["job_id"], unique=False)

    op.create_table(
        "interview_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invite_token", sa.String(length=96), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["interview_batches.id"]),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_token"),
    )
    op.create_index(op.f("ix_interview_invites_id"), "interview_invites", ["id"], unique=False)
    op.create_index(op.f("ix_interview_invites_invite_token"), "interview_invites", ["invite_token"], unique=False)
    op.create_index("ix_interview_invites_batch_id", "interview_invites", ["batch_id"], unique=False)
    op.create_index("ix_interview_invites_candidate_profile_id", "interview_invites", ["candidate_profile_id"], unique=False)
    op.create_index("ix_interview_invites_job_id", "interview_invites", ["job_id"], unique=False)
    op.create_index("ix_interview_invites_status_expires_at", "interview_invites", ["status", "expires_at"], unique=False)
    op.create_index(
        "ix_interview_invites_invited_expires_at",
        "interview_invites",
        ["expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'invited'"),
    )

    op.create_table(
        "manual_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_db_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_user_id", sa.Integer(), nullable=False),
        sa.Column("recommendation", sa.String(length=40), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=True),
        sa.Column("score_override", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_db_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_manual_reviews_id"), "manual_reviews", ["id"], unique=False)
    op.create_index("ix_manual_reviews_recommendation", "manual_reviews", ["recommendation"], unique=False)
    op.create_index("ix_manual_reviews_reviewer_user_id", "manual_reviews", ["reviewer_user_id"], unique=False)
    op.create_index("ix_manual_reviews_session_db_id", "manual_reviews", ["session_db_id"], unique=False)

    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invite_id", sa.Integer(), nullable=True),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("provider_message_id", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"]),
        sa.ForeignKeyConstraint(["invite_id"], ["interview_invites.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_logs_id"), "notification_logs", ["id"], unique=False)
    op.create_index("ix_notification_logs_candidate_profile_id", "notification_logs", ["candidate_profile_id"], unique=False)
    op.create_index("ix_notification_logs_invite_id", "notification_logs", ["invite_id"], unique=False)
    op.create_index("ix_notification_logs_status_created_at", "notification_logs", ["status", "created_at"], unique=False)

    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.add_column(sa.Column("job_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("candidate_profile_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("interview_batch_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("invite_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("rubric_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_interview_sessions_job_id_jobs", "jobs", ["job_id"], ["id"])
        batch_op.create_foreign_key(
            "fk_interview_sessions_candidate_profile_id_candidate_profiles",
            "candidate_profiles",
            ["candidate_profile_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_interview_sessions_interview_batch_id_interview_batches",
            "interview_batches",
            ["interview_batch_id"],
            ["id"],
        )
        batch_op.create_foreign_key("fk_interview_sessions_invite_id_interview_invites", "interview_invites", ["invite_id"], ["id"])
        batch_op.create_foreign_key("fk_interview_sessions_rubric_id_evaluation_rubrics", "evaluation_rubrics", ["rubric_id"], ["id"])
        batch_op.create_index("ix_interview_sessions_job_id", ["job_id"], unique=False)
        batch_op.create_index("ix_interview_sessions_candidate_profile_id", ["candidate_profile_id"], unique=False)
        batch_op.create_index("ix_interview_sessions_interview_batch_id", ["interview_batch_id"], unique=False)
        batch_op.create_index("ix_interview_sessions_invite_id", ["invite_id"], unique=False)
        batch_op.create_index("ix_interview_sessions_rubric_id", ["rubric_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.drop_index("ix_interview_sessions_rubric_id")
        batch_op.drop_index("ix_interview_sessions_invite_id")
        batch_op.drop_index("ix_interview_sessions_interview_batch_id")
        batch_op.drop_index("ix_interview_sessions_candidate_profile_id")
        batch_op.drop_index("ix_interview_sessions_job_id")
        batch_op.drop_constraint("fk_interview_sessions_rubric_id_evaluation_rubrics", type_="foreignkey")
        batch_op.drop_constraint("fk_interview_sessions_invite_id_interview_invites", type_="foreignkey")
        batch_op.drop_constraint("fk_interview_sessions_interview_batch_id_interview_batches", type_="foreignkey")
        batch_op.drop_constraint("fk_interview_sessions_candidate_profile_id_candidate_profiles", type_="foreignkey")
        batch_op.drop_constraint("fk_interview_sessions_job_id_jobs", type_="foreignkey")
        batch_op.drop_column("rubric_id")
        batch_op.drop_column("invite_id")
        batch_op.drop_column("interview_batch_id")
        batch_op.drop_column("candidate_profile_id")
        batch_op.drop_column("job_id")

    op.drop_index("ix_notification_logs_status_created_at", table_name="notification_logs")
    op.drop_index("ix_notification_logs_invite_id", table_name="notification_logs")
    op.drop_index("ix_notification_logs_candidate_profile_id", table_name="notification_logs")
    op.drop_index(op.f("ix_notification_logs_id"), table_name="notification_logs")
    op.drop_table("notification_logs")

    op.drop_index("ix_manual_reviews_session_db_id", table_name="manual_reviews")
    op.drop_index("ix_manual_reviews_reviewer_user_id", table_name="manual_reviews")
    op.drop_index("ix_manual_reviews_recommendation", table_name="manual_reviews")
    op.drop_index(op.f("ix_manual_reviews_id"), table_name="manual_reviews")
    op.drop_table("manual_reviews")

    op.drop_index("ix_interview_invites_invited_expires_at", table_name="interview_invites")
    op.drop_index("ix_interview_invites_status_expires_at", table_name="interview_invites")
    op.drop_index("ix_interview_invites_job_id", table_name="interview_invites")
    op.drop_index("ix_interview_invites_candidate_profile_id", table_name="interview_invites")
    op.drop_index("ix_interview_invites_batch_id", table_name="interview_invites")
    op.drop_index(op.f("ix_interview_invites_invite_token"), table_name="interview_invites")
    op.drop_index(op.f("ix_interview_invites_id"), table_name="interview_invites")
    op.drop_table("interview_invites")

    op.drop_index("ix_evaluation_rubrics_job_id", table_name="evaluation_rubrics")
    op.drop_index("ix_evaluation_rubrics_is_active", table_name="evaluation_rubrics")
    op.drop_index(op.f("ix_evaluation_rubrics_id"), table_name="evaluation_rubrics")
    op.drop_table("evaluation_rubrics")

    op.drop_index("ix_interview_batches_status_created_at", table_name="interview_batches")
    op.drop_index("ix_interview_batches_job_id", table_name="interview_batches")
    op.drop_index(op.f("ix_interview_batches_id"), table_name="interview_batches")
    op.drop_table("interview_batches")

    op.drop_index("ix_candidate_profiles_user_id", table_name="candidate_profiles")
    op.drop_index("ix_candidate_profiles_status_created_at", table_name="candidate_profiles")
    op.drop_index("ix_candidate_profiles_resume_profile_id", table_name="candidate_profiles")
    op.drop_index("ix_candidate_profiles_email", table_name="candidate_profiles")
    op.drop_index("ix_candidate_profiles_created_by_user_id", table_name="candidate_profiles")
    op.drop_index(op.f("ix_candidate_profiles_id"), table_name="candidate_profiles")
    op.drop_table("candidate_profiles")

    op.drop_index("ix_jobs_status_created_at", table_name="jobs")
    op.drop_index("ix_jobs_created_by_user_id", table_name="jobs")
    op.drop_index(op.f("ix_jobs_id"), table_name="jobs")
    op.drop_table("jobs")
