"""FR-07: Сурагчийн бодлоготой ижил төрлийн, алхамчилсан бодолттой бодлогыг сангаас сонгоно.

Эрэмбэ: (1) ML-ийн санал болгосон дэд сэдэвтэй таарах (жагсаалтын эхнийх түрүүнд),
(2) түвшний ойр байдал, (3) сурагчийн өмнө нь бодоогүй, (4) бага ID. Зөвхөн бодолтын алхамтай
бодлогуудаас сонгоно; `exclude`-д буй ID-г алгасна ("өөр жишээ үзэх").
"""

from typing import Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Problem
from app.models.learning import Attempt


def find_similar(
    db: Session,
    user_id: int,
    topic_id: str,
    difficulty: Optional[int] = None,
    subtopics: Optional[List[str]] = None,
    exclude: Iterable[int] = (),
) -> Optional[Problem]:
    exclude = set(exclude)
    pool = [
        p
        for p in db.scalars(select(Problem).where(Problem.topic_id == topic_id))
        if p.solution_steps and p.id not in exclude
    ]
    if not pool:
        return None
    attempted = set(
        db.scalars(
            select(Attempt.problem_id).where(
                Attempt.user_id == user_id, Attempt.topic_id == topic_id
            )
        )
    )
    ranks = {s.lower(): i for i, s in enumerate(subtopics or [])}
    want = difficulty or 2

    def key(p: Problem):
        sub_rank = ranks.get((p.subtopic or "").lower(), len(ranks))
        return (sub_rank, abs(p.difficulty - want), p.id in attempted, p.id)

    return min(pool, key=key)
