"""Бүртгэлтэй хэрэглэгчдийг жагсаах.

Хэрэглээ (backend хавтсанд, venv идэвхтэй үед):
    python -m app.list_users            # бүгд
    python -m app.list_users student    # зөвхөн нэг role (student / parent / admin)
"""

import sys

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.database import SessionLocal, init_dev_db
from app.models.user import Role, User


def main() -> None:
    role = None
    if len(sys.argv) > 1:
        try:
            role = Role(sys.argv[1])
        except ValueError:
            print(__doc__)
            sys.exit(1)
    init_dev_db()
    stmt = select(User).order_by(User.id)
    if role:
        stmt = stmt.where(User.role == role)
    with SessionLocal() as db:
        users = db.scalars(stmt).all()
    for u in users:
        created = u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "-"
        print(f"{u.id:>4}  {u.role.value:<8}  {u.email:<32}  {u.full_name:<24}  {created}")
    print(f"Нийт: {len(users)}")


if __name__ == "__main__":
    main()
