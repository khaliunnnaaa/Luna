"""Сурагчийн суралцах явцын хүснэгтүүд (FR-05, FR-08, FR-10, FR-03, FR-14).

- attempts            сурагчийн хариулт бүр (зөв/буруу, алдааны төрөл, хэдэн сануулга ашигласан)
- mastery             сэдэв бүрийн эзэмшлийн магадлал (BKT) — ml/state/*.json-ы оронд DB-д
- term_clicks         сурагч аль нэр томьёон дээр дарсан (сул талын дохио)
- uploads             оруулсан бодлогын зураг ба OCR үр дүн
- parent_child_links  эцэг эх ↔ хүүхэд
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"), index=True
    )
    topic_id: Mapped[str] = mapped_column(String(64), index=True)  # шалгахад хурдан хайхад
    answer: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    # Алдааны төрөл (FR-10): empty, unparsable, sign_error, partial, wrong; зөв бол None
    error_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)  # 0–3 (FR-06/08)
    mastery_before: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mastery_after: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Mastery(Base):
    __tablename__ = "mastery"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[str] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    p_mastery: Mapped[float] = mapped_column(Float)  # 0–1, BKT
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TermClick(Base):
    __tablename__ = "term_clicks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    term: Mapped[str] = mapped_column(String(120), index=True)
    problem_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("problems.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    object_key: Mapped[str] = mapped_column(String(255))  # S3/MinIO дахь түлхүүр
    # pending → done | failed ; ML ажиллахгүй үед failed, сурагч гараар бичнэ (NFR-07)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_latex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    edited_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # сурагчийн засвар
    predicted_topic: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ParentChildLink(Base):
    __tablename__ = "parent_child_links"

    parent_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    child_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PlacementSession(Base):
    """FR-02: Түвшин тогтоох богино adaptive тест (8–10 асуулт)."""

    __tablename__ = "placement_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | done
    total: Mapped[int] = mapped_column(Integer)  # асуултын тоо
    difficulty: Mapped[int] = mapped_column(Integer, default=2)  # дараагийн асуултын түвшин
    # Асуусан асуултууд, дараалсан: [{problem_id, topic_id, difficulty, answer, correct}]
    items: Mapped[list] = mapped_column(JSON, default=list)
    # Асуух сэдвүүдийн дараалал (топологи): ["T01", "T02", ...]
    topic_queue: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
