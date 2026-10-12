"""Supabase: бүх хүснэгт дээр Row Level Security асаана (policy-гүй).

Supabase `public` schema-г anon key-ээр REST (PostgREST) API-д автоматаар нээдэг. RLS асаалттай,
policy байхгүй бол тэр API юу ч буцаахгүй — users.password_hash, хүүхдийн хариулт
задрахгүй (NFR-06).
Backend `postgres` (хүснэгтийн эзэн) эрхээр холбогддог тул RLS түүнд нөлөөлөхгүй.
SQLite болон энгийн PostgreSQL дээр хоргүй (SQLite-д алгасна).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "users", "topics", "topic_prerequisites", "terms", "problems",
    "attempts", "mastery", "term_clicks", "uploads", "parent_child_links",
    "placement_sessions", "alembic_version",
)


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    for t in TABLES:
        op.execute(f'ALTER TABLE "{t}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    for t in TABLES:
        op.execute(f'ALTER TABLE "{t}" DISABLE ROW LEVEL SECURITY')
