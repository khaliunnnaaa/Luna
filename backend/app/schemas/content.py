import re
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.answer_checker import can_parse

TOPIC_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{1,63}$")


def _strip_list(items: List[str]) -> List[str]:
    return [s.strip() for s in items if s and s.strip()]


# ---------- Сэдэв ----------
class TopicIn(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=120)
    grade: int = Field(default=10, ge=1, le=14)
    description: Optional[str] = None
    prerequisites: List[str] = []

    @field_validator("id")
    @classmethod
    def check_id(cls, v: str) -> str:
        v = v.strip()
        if not TOPIC_ID_RE.match(v):
            raise ValueError("ID нь латин үсэг, тоо, _ -аас бүрдэнэ (жишээ: T11)")
        return v


class TopicOut(BaseModel):
    id: str
    name: str
    grade: int
    description: Optional[str]
    prerequisites: List[str]
    problem_count: int = 0


# ---------- Нэр томьёо ----------
class TermIn(BaseModel):
    term: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=1)
    example: Optional[str] = None
    topic_id: Optional[str] = None

    @field_validator("term", "explanation")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Хоосон байж болохгүй")
        return v


class TermOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term: str
    explanation: str
    example: Optional[str]
    topic_id: Optional[str]


# ---------- Бодлого ----------
class ProblemIn(BaseModel):
    code: Optional[str] = Field(default=None, max_length=32)
    topic_id: str
    subtopic: Optional[str] = Field(default=None, max_length=120)
    difficulty: int = Field(default=1, ge=1, le=3)
    statement: str = Field(min_length=1)
    answers: List[str]
    hints: List[str] = []
    solution_steps: List[str] = []
    common_mistakes: Optional[str] = None
    terms: List[str] = []
    source: Optional[str] = Field(default=None, max_length=200)

    @field_validator("code")
    @classmethod
    def empty_code_to_none(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() or None if v else None

    @field_validator("answers")
    @classmethod
    def check_answers(cls, v: List[str]) -> List[str]:
        v = _strip_list(v)
        if not v:
            raise ValueError("Дор хаяж нэг хариу оруулна уу")
        bad = [a for a in v if not can_parse(a)]
        if bad:
            raise ValueError(
                f"Хариуг уншиж чадсангүй: {', '.join(bad)} (жишээ: 1/2, [3, 4], {{x: 7, y: 3}})"
            )
        return v

    @field_validator("hints")
    @classmethod
    def check_hints(cls, v: List[str]) -> List[str]:
        v = _strip_list(v)
        if len(v) > 3:
            raise ValueError("Сануулга 3-аас ихгүй байна")
        return v

    @field_validator("solution_steps")
    @classmethod
    def clean_steps(cls, v: List[str]) -> List[str]:
        v = _strip_list(v)
        if len(v) > 12:
            raise ValueError("Бодолтын алхам 12-оос ихгүй байна")
        return v

    @field_validator("terms")
    @classmethod
    def clean_terms(cls, v: List[str]) -> List[str]:
        return list(dict.fromkeys(_strip_list(v)))

    @field_validator("subtopic", "common_mistakes", "source")
    @classmethod
    def blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        return (v.strip() or None) if v else None


class ProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: Optional[str]
    topic_id: str
    subtopic: Optional[str]
    difficulty: int
    statement: str
    answers: List[str]
    hints: List[str]
    solution_steps: List[str]
    common_mistakes: Optional[str]
    terms: List[str]
    source: Optional[str]
