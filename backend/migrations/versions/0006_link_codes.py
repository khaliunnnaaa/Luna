"""FR-14: link_codes — эцэг эх ↔ хүүхдийг холбох нэг удаагийн код.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "link_codes",
        sa.Column("code", sa.String(length=12), primary_key=True),
        sa.Column(
            "child_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_link_codes_child_id", "link_codes", ["child_id"], unique=True)
    # Supabase: шинэ хүснэгт бүрт RLS заавал (0005-г үз)
    if op.get_context().dialect.name == "postgresql":
        op.execute('ALTER TABLE "link_codes" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index("ix_link_codes_child_id", table_name="link_codes")
    op.drop_table("link_codes")
