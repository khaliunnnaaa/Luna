"""FR-02: Түвшин тогтоох богино adaptive тест (8–10 асуулт, ≤10 мин)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.content import Topic
from app.models.learning import PlacementSession
from app.models.user import Role, User
from app.schemas.placement import (
    PlacementAnswerIn,
    PlacementAnswerOut,
    PlacementQuestion,
    PlacementState,
    PlacementTopicResult,
)
from app.services import placement as svc
from app.services.answer_checker import CORRECT_FEEDBACK

router = APIRouter(prefix="/placement", tags=["placement"])
student = Depends(require_role(Role.student))

WRONG_FEEDBACK = "Зүгээр, энэ бол зөвхөн түвшин тогтоох асуулт. Үргэлжлүүлье."


def _state(db: Session, s: PlacementSession) -> PlacementState:
    if s.status == "done":
        rows = svc.summary(db, s)
        return PlacementState(
            status="done",
            index=len(s.items),
            total=s.total,
            started_at=s.started_at,
            result=[PlacementTopicResult(**r) for r in rows],
            correct_count=sum(1 for it in s.items if it["correct"]),
        )
    q = svc.current_question(db, s)
    question = None
    if q is not None:
        topic = db.get(Topic, q.topic_id)
        question = PlacementQuestion(
            problem_id=q.id,
            topic_id=q.topic_id,
            topic_name=topic.name if topic else q.topic_id,
            difficulty=q.difficulty,
            statement=q.statement,
            terms=q.terms or [],
        )
    started = s.started_at if s.started_at.tzinfo else s.started_at.replace(tzinfo=timezone.utc)
    left = int((started + svc.TIME_LIMIT - datetime.now(timezone.utc)).total_seconds())
    return PlacementState(
        status="active",
        index=len(s.items),
        total=s.total,
        question=question,
        started_at=s.started_at,
        seconds_left=max(0, left),
        correct_count=sum(1 for it in s.items if it["correct"]),
    )


@router.get("", response_model=PlacementState)
def get_state(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Идэвхтэй тест байвал түүний төлөв; үгүй бол сүүлийн үр дүн; аль нь ч үгүй бол none."""
    s = svc.active_session(db, user.id)
    if s and svc.expired(s):
        svc.finish(db, s)
        db.commit()
    if s:
        return _state(db, s)
    done = svc.last_done(db, user.id)
    return _state(db, done) if done else PlacementState(status="none")


@router.post("/start", response_model=PlacementState, dependencies=[student])
def start_test(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Шинэ тест эхлүүлнэ (идэвхтэй байвал үргэлжлүүлнэ). Дахин өгч болно — mastery шинэчлэгдэнэ."""
    try:
        s = svc.start(db, user.id)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e)) from None
    return _state(db, s)


@router.post("/answer", response_model=PlacementAnswerOut, dependencies=[student])
def answer_question(
    data: PlacementAnswerIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = svc.active_session(db, user.id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Идэвхтэй тест алга")
    try:
        ok, err = svc.answer(db, s, data.problem_id, data.answer)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e)) from None
    return PlacementAnswerOut(
        correct=ok,
        error_type=err,
        feedback=CORRECT_FEEDBACK if ok else WRONG_FEEDBACK,
        state=_state(db, s),
    )


@router.post("/finish", response_model=PlacementState, dependencies=[student])
def finish_early(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Хугацаа дууссан эсвэл сурагч зогсоосон: хариулсан асуултаар нь mastery тогтооно."""
    s = svc.active_session(db, user.id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Идэвхтэй тест алга")
    svc.finish(db, s)
    db.commit()
    return _state(db, s)
