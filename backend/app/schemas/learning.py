"""Сурагчийн суралцах урсгалын схемүүд (FR-05, FR-06, FR-08, FR-10)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProblemStudentOut(BaseModel):
    """Сурагчид харуулах бодлого — зөв хариу, сануулгыг ОРУУЛАХГҮЙ (FR-06: хариу шууд өгөхгүй)."""

    id: int
    code: Optional[str]
    topic_id: str
    topic_name: str
    subtopic: Optional[str]
    difficulty: int
    statement: str
    terms: List[str]
    hint_count: int
    my_attempts: int  # энэ сурагч энэ бодлогод хэдэн удаа оролдсон
    solved: bool


class NextOut(BaseModel):
    """FR-09: дараагийн дасгал. Сэдэвт бодлого байхгүй бол problem=None."""

    problem: Optional[ProblemStudentOut]
    topic_id: str
    reason: str
    target_difficulty: int


class HintOut(BaseModel):
    level: int  # 1–3
    hint: str
    hint_count: int


class AttemptIn(BaseModel):
    answer: str = Field(max_length=300)
    hints_used: int = Field(default=0, ge=0, le=3)


class AttemptOut(BaseModel):
    is_correct: bool
    error_type: Optional[str]
    feedback: str
    topic_id: str
    mastery_before: float
    mastery_after: float
    attempts_on_problem: int


class AttemptHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    problem_id: int
    topic_id: str
    answer: str
    is_correct: bool
    error_type: Optional[str]
    hints_used: int
    created_at: datetime


class MasteryOut(BaseModel):
    topic_id: str
    name: str
    grade: int
    p_mastery: float
    attempts_count: int
    correct_count: int
    mastered: bool
    prerequisites: List[str]


class TermClickIn(BaseModel):
    term: str = Field(min_length=1, max_length=120)
    problem_id: Optional[int] = None


class TermPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term: str
    explanation: str
    example: Optional[str]
    topic_id: Optional[str]
