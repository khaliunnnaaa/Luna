"""Суралцах явцын хүснэгтүүд: attempts, mastery, term_clicks, uploads, parent_child_links.

FR-05, FR-08, FR-10 (attempts/mastery/term_clicks), FR-03 (uploads), FR-14 (parent_child_links).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("problem_id", sa.Integer(), sa.ForeignKey("problems.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("topic_id", sa.String(64), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("error_type", sa.String(32), nullable=True),
        sa.Column("hints_used", sa.Integer(), nullable=False),
        sa.Column("mastery_before", sa.Float(), nullable=True),
        sa.Column("mastery_after", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_attempts_user_id", "attempts", ["user_id"])
    op.create_index("ix_attempts_problem_id", "attempts", ["problem_id"])
    op.create_index("ix_attempts_topic_id", "attempts", ["topic_id"])

    op.create_table(
        "mastery",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("topic_id", sa.String(64), sa.ForeignKey("topics.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("p_mastery", sa.Float(), nullable=False),
        sa.Column("attempts_count", sa.Integer(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "term_clicks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("term", sa.String(120), nullable=False),
        sa.Column("problem_id", sa.Integer(), sa.ForeignKey("problems.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_term_clicks_user_id", "term_clicks", ["user_id"])
    op.create_index("ix_term_clicks_term", "term_clicks", ["term"])

    op.create_table(
        "uploads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("object_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("ocr_latex", sa.Text(), nullable=True),
        sa.Column("edited_text", sa.Text(), nullable=True),
        sa.Column("predicted_topic", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_uploads_user_id", "uploads", ["user_id"])

    op.create_table(
        "parent_child_links",
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("child_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("parent_child_links")
    op.drop_table("uploads")
    op.drop_table("term_clicks")
    op.drop_table("mastery")
    op.drop_table("attempts")
