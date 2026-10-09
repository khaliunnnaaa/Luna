"""FR-02: Түвшин тогтоох тестийн схем."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PlacementQuestion(BaseModel):
    problem_id: int
    topic_id: str
    topic_name: str
    difficulty: int
    statement: str
    terms: List[str]


class PlacementTopicResult(BaseModel):
    topic_id: str
    topic_name: str
    difficulty: int
    correct: bool
    p_mastery: float


class PlacementState(BaseModel):
    status: str  # none | active | done
    index: int = 0  # хариулсан асуултын тоо
    total: int = 0
    question: Optional[PlacementQuestion] = None
    started_at: Optional[datetime] = None
    seconds_left: Optional[int] = None
    result: List[PlacementTopicResult] = []
    correct_count: int = 0


class PlacementAnswerIn(BaseModel):
    problem_id: int
    answer: str = Field(default="", max_length=300)  # хоосон = "мэдэхгүй"


class PlacementAnswerOut(BaseModel):
    correct: bool
    error_type: Optional[str]
    feedback: str
    state: PlacementState
