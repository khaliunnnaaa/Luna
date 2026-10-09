"""FR-03 зураг оруулах / FR-04 ангилах схем."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ClassifyIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ClassifyOut(BaseModel):
    available: bool  # ML сервис хариулсан эсэх
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None
    difficulty: Optional[int] = None
    confidence: Optional[float] = None
    subtopics: List[str] = []
    terms: List[str] = []  # текстэнд таарсан толийн нэр томьёо (FR-05)


class UploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str  # pending | done | failed
    ocr_text: Optional[str]
    ocr_latex: Optional[str]
    edited_text: Optional[str]
    predicted_topic: Optional[str]
    created_at: datetime


class UploadDetailOut(UploadOut):
    topic_name: Optional[str] = None
    ml_available: bool = True
    message: str = ""


class UploadEditIn(BaseModel):
    edited_text: str = Field(min_length=1, max_length=2000)
