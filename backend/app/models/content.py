"""FR-16: Сэдэв, нэр томьёо, бодлогын сан."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Сэдвүүдийн өмнөх–дараах холбоо (prerequisite граф)
topic_prerequisites = Table(
    "topic_prerequisites",
    Base.metadata,
    Column("topic_id", String(64), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "prerequisite_id", String(64), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Topic(Base):
    __tablename__ = "topics"

    # ML хэсэгтэй ижил код: "T01" … "T10" (ml/config/topics.csv)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    grade: Mapped[int] = mapped_column(Integer, default=10)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    prerequisites: Mapped[List["Topic"]] = relationship(
        "Topic",
        secondary=topic_prerequisites,
        primaryjoin=lambda: Topic.id == topic_prerequisites.c.topic_id,
        secondaryjoin=lambda: Topic.id == topic_prerequisites.c.prerequisite_id,
        order_by=lambda: Topic.id,
    )


class Term(Base):
    __tablename__ = "terms"

    id: Mapped[int] = mapped_column(primary_key=True)
    term: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    explanation: Mapped[str] = mapped_column(Text)
    example: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    topic_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)
    subtopic: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    # 1 (хялбар) – 3 (хүнд), ML хэсгийн `түвшин(1-3)`-тэй ижил
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    # Текст + LaTeX томьёо: "Тэгшитгэлийг бод: $x^2 - 5x + 6 = 0$"
    statement: Mapped[str] = mapped_column(Text)
    answers: Mapped[List[str]] = mapped_column(JSON, default=list)  # SymPy-д уншигдах хэлбэрээр
    hints: Mapped[List[str]] = mapped_column(JSON, default=list)  # 3 шатны сануулга (FR-06)
    # FR-07: алхамчилсан бүрэн бодолт — зөвхөн "ижил төстэй бодлого"-оор тайлбарлахад харуулна
    solution_steps: Mapped[List[str]] = mapped_column(JSON, default=list)
    common_mistakes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # FR-08/10-д
    terms: Mapped[List[str]] = mapped_column(JSON, default=list)  # холбоотой нэр томьёо (FR-05)
    source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
