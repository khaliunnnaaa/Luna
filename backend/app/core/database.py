"""Өгөгдлийн сантай холбогдох тохиргоо."""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Хүсэлт бүрт нэг session нээж, дуусахад хаана."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
