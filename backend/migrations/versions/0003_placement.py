"""FR-02: placement_sessions — түвшин тогтоох тестийн явц ба үр дүн.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "placement_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("topic_queue", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_placement_sessions_user_id", "placement_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_table("placement_sessions")
