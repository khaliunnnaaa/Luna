"""Сурагчийн суралцах урсгал: бодлого харах → сануулга → хариу → mastery.

FR-05 нэр томьёо, FR-06 сануулга, FR-08 mastery (BKT), FR-10 хариу шалгах.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.content import Problem, Term, Topic
from app.models.learning import Attempt, TermClick
from app.models.user import Role, User
from app.schemas.learning import (
    AttemptHistoryOut,
    AttemptIn,
    AttemptOut,
    HintOut,
    MasteryOut,
    NextOut,
    ProblemStudentOut,
    TermClickIn,
    TermPublicOut,
)
from app.services import mastery as mastery_svc
from app.services import recommender
from app.services.answer_checker import CORRECT_FEEDBACK, ERROR_FEEDBACK, check_answer

router = APIRouter(tags=["learning"])
student = Depends(require_role(Role.student))


def _problem_or_404(db: Session, problem_id: int) -> Problem:
    p = db.get(Problem, problem_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Бодлого олдсонгүй")
    return p


def _attempt_stats(db: Session, user_id: int, problem_id: int):
    """(оролдлогын тоо, бодсон эсэх)"""
    n = db.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(Attempt.user_id == user_id, Attempt.problem_id == problem_id)
    )
    solved = db.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(
            Attempt.user_id == user_id,
            Attempt.problem_id == problem_id,
            Attempt.is_correct.is_(True),
        )
    )
    return int(n or 0), bool(solved)


# ================= Нэр томьёо (FR-05) =================
@router.get("/terms", response_model=List[TermPublicOut])
def list_terms_public(db: Session = Depends(get_db)) -> List[Term]:
    """Нэр томьёоны толь — нэвтрэлт шаардахгүй."""
    return list(db.scalars(select(Term).order_by(Term.term)))


@router.post("/term-clicks", status_code=status.HTTP_201_CREATED)
def record_term_click(
    data: TermClickIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    """Сурагч аль үгийг ойлгоогүйг бүртгэнэ — мэдлэгийн цоорхойн дохио (FR-05/08)."""
    term = data.term.strip()
    if data.problem_id is not None and db.get(Problem, data.problem_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Бодлого олдсонгүй")
    db.add(TermClick(user_id=user.id, term=term, problem_id=data.problem_id))
    db.commit()
    t = db.scalar(select(Term).where(Term.term == term))
    return {
        "term": term,
        "explanation": t.explanation if t else None,
        "example": t.example if t else None,
    }


# ================= Бодлого (сурагчийн харагдац) =================
def _student_view(db: Session, p: Problem, user: User) -> ProblemStudentOut:
    topic = db.get(Topic, p.topic_id)
    n, solved = _attempt_stats(db, user.id, p.id)
    return ProblemStudentOut(
        id=p.id,
        code=p.code,
        topic_id=p.topic_id,
        topic_name=topic.name if topic else p.topic_id,
        subtopic=p.subtopic,
        difficulty=p.difficulty,
        statement=p.statement,
        terms=p.terms or [],
        hint_count=len(p.hints or []),
        my_attempts=n,
        solved=solved,
    )


@router.get("/problems/{problem_id}", response_model=ProblemStudentOut)
def get_problem_for_student(
    problem_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ProblemStudentOut:
    return _student_view(db, _problem_or_404(db, problem_id), user)


@router.get("/next", response_model=NextOut)
def next_problem(
    topic_id: Optional[str] = Query(default=None, description="FR-11: сурагчийн сонгосон сэдэв"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NextOut:
    """FR-09: мэдлэгийн цоорхой ба түвшинд тохирсон дараагийн дасгал."""
    if topic_id and db.get(Topic, topic_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Сэдэв олдсонгүй")
    problem, tid, reason, level = recommender.recommend(db, user.id, topic_id)
    return NextOut(
        problem=_student_view(db, problem, user) if problem else None,
        topic_id=tid,
        reason=reason,
        target_difficulty=level,
    )


@router.get("/problems/{problem_id}/hints/{level}", response_model=HintOut)
def get_hint(
    problem_id: int,
    level: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HintOut:
    """FR-06: сануулгыг шатлан (1 → 2 → 3) өгнө. Хэдийг ашигласныг хариу илгээхдээ дамжуулна."""
    p = _problem_or_404(db, problem_id)
    hints = p.hints or []
    if level < 1 or level > len(hints):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Энэ бодлогод {len(hints)} сануулга бий"
        )
    return HintOut(level=level, hint=hints[level - 1], hint_count=len(hints))


@router.post(
    "/problems/{problem_id}/attempt",
    response_model=AttemptOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[student],
)
def submit_attempt(
    problem_id: int,
    data: AttemptIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttemptOut:
    """FR-10: хариуг SymPy-ээр шалгаж, алдааны төрөл тэмдэглэж, FR-08: BKT-ээр mastery шинэчилнэ.

    Зөв хариуг хэзээ ч буцаахгүй (FR-06). Аль хэдийн бодсон бодлогыг дахин бодвол mastery
    өөрчлөгдөхгүй (давтан зөв хариулж mastery-г хуурахаас сэргийлнэ).
    """
    p = _problem_or_404(db, problem_id)
    is_correct, error_type = check_answer(data.answer, p.answers or [])
    _, already_solved = _attempt_stats(db, user.id, p.id)

    m = mastery_svc.get_or_create(db, user.id, p.topic_id)
    before = m.p_mastery
    if not already_solved:
        m = mastery_svc.record_answer(db, user.id, p.topic_id, is_correct)
    after = m.p_mastery

    db.add(
        Attempt(
            user_id=user.id,
            problem_id=p.id,
            topic_id=p.topic_id,
            answer=data.answer.strip(),
            is_correct=is_correct,
            error_type=error_type,
            hints_used=data.hints_used,
            mastery_before=before,
            mastery_after=after,
        )
    )
    db.commit()
    n, _ = _attempt_stats(db, user.id, p.id)
    return AttemptOut(
        is_correct=is_correct,
        error_type=error_type,
        feedback=CORRECT_FEEDBACK if is_correct else ERROR_FEEDBACK[error_type],
        topic_id=p.topic_id,
        mastery_before=round(before, 4),
        mastery_after=round(after, 4),
        attempts_on_problem=n,
    )


# ================= Миний ахиц (FR-08 / FR-12-ийн суурь) =================
@router.get("/me/mastery", response_model=List[MasteryOut])
def my_mastery(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Бүх сэдвийн эзэмшил. Оролдоогүй сэдэвт BKT-ийн анхны (prior) утгыг харуулна."""
    return [MasteryOut(**m) for m in mastery_svc.overview(db, user.id)]


@router.get("/me/attempts", response_model=List[AttemptHistoryOut])
def my_attempts(
    limit: int = Query(default=20, ge=1, le=200),
    topic_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[Attempt]:
    q = select(Attempt).where(Attempt.user_id == user.id).order_by(Attempt.id.desc()).limit(limit)
    if topic_id:
        q = q.where(Attempt.topic_id == topic_id)
    return list(db.scalars(q))
