"""Эхний схем: users, topics, topic_prerequisites, terms, problems (FR-01, FR-16).

`Base.metadata.create_all`-оор үүссэн хуучин DB-д: `alembic stamp 0001`.

Revision ID: 0001
Revises:
Create Date: 2026-10-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("student", "parent", "admin", name="role"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "topics",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "topic_prerequisites",
        sa.Column("topic_id", sa.String(64), sa.ForeignKey("topics.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("prerequisite_id", sa.String(64),
                  sa.ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("term", sa.String(120), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("example", sa.Text(), nullable=True),
        sa.Column("topic_id", sa.String(64), sa.ForeignKey("topics.id", ondelete="SET NULL"),
                  nullable=True),
    )
    op.create_index("ix_terms_term", "terms", ["term"], unique=True)

    op.create_table(
        "problems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=True, unique=True),
        sa.Column("topic_id", sa.String(64), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("subtopic", sa.String(120), nullable=True),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("hints", sa.JSON(), nullable=False),
        sa.Column("common_mistakes", sa.Text(), nullable=True),
        sa.Column("terms", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_problems_topic_id", "problems", ["topic_id"])


def downgrade() -> None:
    op.drop_table("problems")
    op.drop_table("terms")
    op.drop_table("topic_prerequisites")
    op.drop_table("topics")
    op.drop_table("users")
