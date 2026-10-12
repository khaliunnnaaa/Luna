"""FR-07: problems.solution_steps (алхамчилсан бодолт), uploads.outcome.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("problems") as b:
        b.add_column(sa.Column("solution_steps", sa.JSON(), nullable=False, server_default="[]"))
    with op.batch_alter_table("uploads") as b:
        b.add_column(sa.Column("outcome", sa.String(16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("uploads") as b:
        b.drop_column("outcome")
    with op.batch_alter_table("problems") as b:
        b.drop_column("solution_steps")
