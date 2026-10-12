"""Өгөгдлийн сантай холбогдох тохиргоо."""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
# pool_pre_ping: Supabase pooler сул холболтыг хаадаг — тасарсан холболтыг шалгаж дахин нээнэ
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_dev_db() -> None:
    """SQLite (dev) дээр хүснэгтийг шууд үүсгэнэ. PostgreSQL-д зөвхөн Alembic — create_all
    хийвэл alembic_version-гүй хүснэгт үүсч, дараа `upgrade head` "already exists" алдаа өгнө."""
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Хүсэлт бүрт нэг session нээж, дуусахад хаана."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
