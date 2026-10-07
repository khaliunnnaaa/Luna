"""Веб backend-ээс ML хэсгийг дуудах цорын ганц цэг.

    from ml.api import classify_problem, update_mastery, recommend_next, recognize_image
"""
from __future__ import annotations

from ml.classifier import predict as _clf
from ml.recommender import recommend as _rec
from ml.tracing import mastery as _mastery

_store = _mastery.JSONStudentStore()


def classify_problem(text: str) -> dict:
    """Бодлогын текстээс (монгол + LaTeX) сэдэв, хүндийн зэрэг (1–3), итгэлийг таамаглана.
    -> {"topic": "T03", "difficulty": 2, "confidence": 0.81}"""
    r = _clf.predict(text)
    return {"topic": r["topic"], "difficulty": r["difficulty"], "confidence": r["confidence"]}


def update_mastery(student_id: str, topic: str, correct: bool) -> dict[str, float]:
    """Хариултыг бүртгэж BKT-ээр шинэчилнэ. -> {"T01": 0.72, ..., "T10": 0.69}"""
    return _mastery.update_mastery(student_id, topic, correct, store=_store)


def recommend_next(student_id: str) -> dict:
    """-> {"problem_id": "T02-008", "topic": "T02", "difficulty": 1, "reason": "..."}"""
    state = _mastery.get_state(student_id, _store)
    result = _rec.recommend(state)
    if result["problem_id"]:
        state["recommended"].append(result["problem_id"])
        _store.save(student_id, state)
    return result


def recognize_image(path: str) -> dict:
    """Зургаас бодлого таних. -> {"text": "...", "latex": ["x^2-4=0"]}"""
    from ml.ocr.pipeline import recognize  # pix2tex/torch-ийг шаардлагатай үед л ачаална
    return recognize(path)


def register_student(student_id: str, grade: int = 10) -> dict:
    """Нэмэлт туслах: шинэ сурагчийг ангийн хамт бүртгэнэ (байгаа бол ангийг шинэчилнэ)."""
    state = _mastery.get_state(student_id, _store, grade=grade)
    state["grade"] = grade
    _store.save(student_id, state)
    return state
