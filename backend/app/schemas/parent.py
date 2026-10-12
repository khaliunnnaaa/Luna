"""FR-14: эцэг эх ↔ хүүхэд холбох, хүүхдийн ахицын тайлан."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.learning import MasteryOut


class LinkCodeOut(BaseModel):
    code: str
    expires_at: datetime


class LinkIn(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class PersonOut(BaseModel):
    id: int
    full_name: str


class SummaryOut(BaseModel):
    topics_total: int
    topics_mastered: int
    attempts_total: int
    attempts_7d: int
    correct_7d: int
    accuracy_7d: Optional[float]
    active_days_14: int
    days_since_active: Optional[int]
    placement_done: bool


class DayActivity(BaseModel):
    date: str
    correct: int
    wrong: int


class TrendPoint(BaseModel):
    date: str
    avg_mastery: float


class ErrorCount(BaseModel):
    type: str
    label: str
    count: int


class FocusTopic(BaseModel):
    topic_id: str
    name: str
    p_mastery: float
    accuracy: float
    weak_prerequisites: List[str]


class Tip(BaseModel):
    kind: str  # start | habit | focus | error | hints | praise
    title: str
    text: str


class ReportOut(BaseModel):
    child: PersonOut
    summary: SummaryOut
    activity: List[DayActivity]
    trend: List[TrendPoint]
    mastery: List[MasteryOut]
    errors: List[ErrorCount]
    hints_avg: Optional[float]
    focus: List[FocusTopic]
    tips: List[Tip]
