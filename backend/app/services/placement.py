"""FR-02: Түвшин тогтоох богино adaptive тест.

Зарчим:
  - 8–10 асуулт (сэдвийн тоогоор, дээд тал нь MAX_QUESTIONS), сэдэв бүрээс нэг асуулт,
    урьдач (prerequisite) дарааллаар — суурь сэдвээс эхэлнэ.
  - Adaptive: 2-р түвшнээс эхэлж, зөв бол дараагийн асуулт нэг түвшин хүнд, буруу бол хялбар.
  - Дуусахад сэдэв бүрийн анхны mastery-г хариулсан түвшин ба зөв/буруугаас тогтооно
    (BKT-ийн ерөнхий prior 0.667 хэт өндөр байсан асуудлыг ингэж шийднэ).
  - Асуугдаагүй сэдэв (сэдэв > 10 бол) BKT-ийн prior-оор үлдэнэ.
  - TIME_LIMIT (10 мин) хэтэрвэл үлдсэн асуултыг асуухгүй дуусгана.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Problem, Topic
from app.models.learning import Attempt, PlacementSession
from app.services import mastery as mastery_svc
from app.services.answer_checker import check_answer
from app.services.recommender import topological_order

MAX_QUESTIONS = 10
TIME_LIMIT = timedelta(minutes=10)

# Хариулсан түвшин → анхны mastery (зөв / буруу)
INITIAL_CORRECT: Dict[int, float] = {1: 0.60, 2: 0.75, 3: 0.90}
INITIAL_WRONG: Dict[int, float] = {1: 0.15, 2: 0.30, 3: 0.45}


def _topics_with_problems(db: Session) -> List[str]:
    """Бодлоготой сэдвүүд, топологийн дарааллаар."""
    topics = {t.id: t for t in db.scalars(select(Topic))}
    have = set(db.scalars(select(Problem.topic_id).distinct()))
    order = topological_order({c: [p.id for p in t.prerequisites] for c, t in topics.items()})
    return [c for c in order if c in have]


def active_session(db: Session, user_id: int) -> Optional[PlacementSession]:
    return db.scalar(
        select(PlacementSession)
        .where(PlacementSession.user_id == user_id, PlacementSession.status == "active")
        .order_by(PlacementSession.id.desc())
    )


def last_done(db: Session, user_id: int) -> Optional[PlacementSession]:
    return db.scalar(
        select(PlacementSession)
        .where(PlacementSession.user_id == user_id, PlacementSession.status == "done")
        .order_by(PlacementSession.id.desc())
    )


def start(db: Session, user_id: int) -> PlacementSession:
    """Идэвхтэй тест байвал түүнийг, үгүй бол шинээр үүсгэнэ. Сэдэв байхгүй бол ValueError."""
    s = active_session(db, user_id)
    if s:
        return s
    queue = _topics_with_problems(db)
    if not queue:
        raise ValueError("Бодлоготой сэдэв байхгүй тул тест өгөх боломжгүй")
    # Сэдэв 10-аас олон бол эхний 10 (суурь сэдвүүд); цөөн бол бүгд
    queue = queue[:MAX_QUESTIONS]
    s = PlacementSession(
        user_id=user_id, status="active", total=len(queue), difficulty=2, items=[],
        topic_queue=queue,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _pick(db: Session, user_id: int, topic_id: str, difficulty: int, exclude: List[int]):
    pool = list(db.scalars(select(Problem).where(Problem.topic_id == topic_id)))
    pool = [p for p in pool if p.id not in exclude] or pool
    if not pool:
        return None
    attempted = set(
        db.scalars(
            select(Attempt.problem_id).where(
                Attempt.user_id == user_id, Attempt.topic_id == topic_id
            )
        )
    )
    return min(pool, key=lambda p: (p.id in attempted, abs(p.difficulty - difficulty), p.id))


def expired(s: PlacementSession) -> bool:
    started = s.started_at
    if started.tzinfo is None:  # SQLite timezone-гүй хадгалдаг
        started = started.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - started > TIME_LIMIT


def current_question(db: Session, s: PlacementSession) -> Optional[Problem]:
    """Дараагийн асуух бодлого; тест дууссан бол None."""
    if s.status != "active":
        return None
    idx = len(s.items)
    if idx >= s.total:
        return None
    asked = [it["problem_id"] for it in s.items]
    return _pick(db, s.user_id, s.topic_queue[idx], s.difficulty, asked)


def answer(
    db: Session, s: PlacementSession, problem_id: int, text: str
) -> Tuple[bool, Optional[str]]:
    """Нэг асуултад хариулна. -> (зөв эсэх, алдааны төрөл). Дуусвал mastery-г тогтооно."""
    if s.status != "active":
        raise ValueError("Тест аль хэдийн дууссан")
    q = current_question(db, s)
    if q is None or q.id != problem_id:
        raise ValueError("Энэ асуулт одоогийн асуулт биш байна")
    ok, err = check_answer(text, q.answers or [])
    items = list(s.items)
    items.append(
        {
            "problem_id": q.id,
            "topic_id": q.topic_id,
            "difficulty": q.difficulty,
            "answer": (text or "").strip(),
            "correct": ok,
        }
    )
    s.items = items
    s.difficulty = min(3, s.difficulty + 1) if ok else max(1, s.difficulty - 1)
    if len(s.items) >= s.total or expired(s):
        finish(db, s)
    db.commit()
    return ok, err


def finish(db: Session, s: PlacementSession) -> Dict[str, float]:
    """Сэдэв бүрийн анхны mastery-г тогтооно (commit хийхгүй)."""
    result: Dict[str, float] = {}
    for it in s.items:
        p = INITIAL_CORRECT if it["correct"] else INITIAL_WRONG
        result[it["topic_id"]] = p[int(it["difficulty"])]
    for topic_id, p in result.items():
        mastery_svc.set_initial(db, s.user_id, topic_id, p)
    s.status = "done"
    s.finished_at = datetime.now(timezone.utc)
    return result


def summary(db: Session, s: PlacementSession) -> List[dict]:
    names = {t.id: t.name for t in db.scalars(select(Topic))}
    out = []
    for it in s.items:
        p = (INITIAL_CORRECT if it["correct"] else INITIAL_WRONG)[int(it["difficulty"])]
        out.append(
            {
                "topic_id": it["topic_id"],
                "topic_name": names.get(it["topic_id"], it["topic_id"]),
                "difficulty": it["difficulty"],
                "correct": it["correct"],
                "p_mastery": p,
            }
        )
    return out
