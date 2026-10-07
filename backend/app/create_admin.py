"""Админ хэрэглэгч үүсгэх.

Хэрэглээ (backend хавтсанд, venv идэвхтэй үед):
    python -m app.create_admin admin@example.com "НууцҮг123" "Админ"
"""

import sys

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.user import Role, User


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    email, password = sys.argv[1].strip().lower(), sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "Админ"
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            print(f"{email} аль хэдийн бүртгэлтэй байна.")
            return
        admin = User(
            email=email,
            full_name=name,
            password_hash=hash_password(password),
            role=Role.admin,
        )
        db.add(admin)
        db.commit()
    print(f"Админ үүслээ: {email}")


if __name__ == "__main__":
    main()
