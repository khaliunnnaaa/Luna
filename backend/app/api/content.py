"""FR-16: Контент удирдлага. Бичих үйлдлүүд зөвхөн админд."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.models.content import Problem, Term, Topic
from app.models.user import Role
from app.schemas.content import ProblemIn, ProblemOut, TermIn, TermOut, TopicIn, TopicOut
from app.services.topic_graph import creates_cycle

admin = Depends(require_role(Role.admin))

public_router = APIRouter(tags=["content"])
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[admin])


# ================= Туслах функцууд =================
def _topic_out(t: Topic, counts: Dict[str, int]) -> TopicOut:
    return TopicOut(
        id=t.id,
        name=t.name,
        grade=t.grade,
        description=t.description,
        prerequisites=[p.id for p in t.prerequisites],
        problem_count=counts.get(t.id, 0),
    )


def _problem_counts(db: Session) -> Dict[str, int]:
    rows = db.execute(select(Problem.topic_id, func.count()).group_by(Problem.topic_id))
    return {tid: n for tid, n in rows}


def _all_topics(db: Session) -> List[TopicOut]:
    counts = _problem_counts(db)
    topics = db.scalars(select(Topic).order_by(Topic.grade, Topic.name)).all()
    return [_topic_out(t, counts) for t in topics]


def _get_or_404(db: Session, model, key, what: str):
    obj = db.get(model, key)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{what} олдсонгүй")
    return obj


def _ensure_topic(db: Session, topic_id: Optional[str]) -> None:
    if topic_id and db.get(Topic, topic_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"'{topic_id}' сэдэв байхгүй байна")


def _set_prerequisites(db: Session, topic: Topic, prereq_ids: List[str]) -> None:
    prereq_ids = list(dict.fromkeys(prereq_ids))  # давхардлыг арилгана
    if topic.id in prereq_ids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Сэдэв өөрийгөө өмнөх сэдэв болгож болохгүй"
        )
    prereqs = []
    for pid in prereq_ids:
        p = db.get(Topic, pid)
        if p is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"'{pid}' сэдэв байхгүй байна")
        prereqs.append(p)
    graph = {t.id: [p.id for p in t.prerequisites] for t in db.scalars(select(Topic))}
    if creates_cycle(graph, topic.id, prereq_ids):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Тойрог холбоо үүсэж байна (A → B → A). Өмнөх сэдвүүдээ шалгана уу.",
        )
    topic.prerequisites = prereqs


def _commit(db: Session, conflict_msg: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=conflict_msg) from None


# ================= Нийтэд нээлттэй =================
@public_router.get("/topics", response_model=List[TopicOut])
def list_topics_public(db: Session = Depends(get_db)) -> List[TopicOut]:
    """Сэдвүүд ба тэдгээрийн холбоо (FR-11 сэдвийн замд ашиглана)."""
    return _all_topics(db)


# ================= Сэдэв =================
@router.get("/topics", response_model=List[TopicOut])
def list_topics(db: Session = Depends(get_db)) -> List[TopicOut]:
    return _all_topics(db)


@router.post("/topics", response_model=TopicOut, status_code=status.HTTP_201_CREATED)
def create_topic(data: TopicIn, db: Session = Depends(get_db)) -> TopicOut:
    if db.get(Topic, data.id):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"'{data.id}' ID-тай сэдэв байна")
    topic = Topic(id=data.id, name=data.name, grade=data.grade, description=data.description)
    db.add(topic)
    db.flush()
    try:
        _set_prerequisites(db, topic, data.prerequisites)
    except HTTPException:
        db.rollback()  # хагас хадгалагдсан өөрчлөлтийг буцаана
        raise
    _commit(db, "Сэдэв хадгалж чадсангүй")
    return _topic_out(topic, _problem_counts(db))


@router.put("/topics/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: str, data: TopicIn, db: Session = Depends(get_db)) -> TopicOut:
    topic = _get_or_404(db, Topic, topic_id, "Сэдэв")
    if data.id != topic_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Сэдвийн ID-г өөрчлөх боломжгүй")
    topic.name, topic.grade, topic.description = data.name, data.grade, data.description
    try:
        _set_prerequisites(db, topic, data.prerequisites)
    except HTTPException:
        db.rollback()
        raise
    _commit(db, "Сэдэв хадгалж чадсангүй")
    return _topic_out(topic, _problem_counts(db))


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(topic_id: str, db: Session = Depends(get_db)) -> Response:
    topic = _get_or_404(db, Topic, topic_id, "Сэдэв")
    if db.scalar(select(func.count()).select_from(Problem).where(Problem.topic_id == topic_id)):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Энэ сэдэвт бодлого байна. Эхлээд бодлогуудыг устгана уу.",
        )
    dependents = [t.name for t in db.scalars(select(Topic)) if topic in t.prerequisites]
    if dependents:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Дараах сэдвүүд үүнээс хамаарна: {', '.join(dependents)}",
        )
    for term in db.scalars(select(Term).where(Term.topic_id == topic_id)):
        term.topic_id = None  # нэр томьёо үлдэнэ, зөвхөн сэдвийн холбоос арилна
    db.delete(topic)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================= Нэр томьёо =================
@router.get("/terms", response_model=List[TermOut])
def list_terms(db: Session = Depends(get_db)) -> List[Term]:
    return list(db.scalars(select(Term).order_by(Term.term)))


@router.post("/terms", response_model=TermOut, status_code=status.HTTP_201_CREATED)
def create_term(data: TermIn, db: Session = Depends(get_db)) -> Term:
    _ensure_topic(db, data.topic_id)
    term = Term(**data.model_dump())
    db.add(term)
    _commit(db, f"'{data.term}' нэр томьёо аль хэдийн байна")
    db.refresh(term)
    return term


@router.put("/terms/{term_id}", response_model=TermOut)
def update_term(term_id: int, data: TermIn, db: Session = Depends(get_db)) -> Term:
    term = _get_or_404(db, Term, term_id, "Нэр томьёо")
    _ensure_topic(db, data.topic_id)
    for k, v in data.model_dump().items():
        setattr(term, k, v)
    _commit(db, f"'{data.term}' нэр томьёо аль хэдийн байна")
    db.refresh(term)
    return term


@router.delete("/terms/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_term(term_id: int, db: Session = Depends(get_db)) -> Response:
    db.delete(_get_or_404(db, Term, term_id, "Нэр томьёо"))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================= Бодлого =================
@router.get("/problems", response_model=List[ProblemOut])
def list_problems(
    topic_id: Optional[str] = Query(default=None),
    difficulty: Optional[int] = Query(default=None, ge=1, le=3),
    db: Session = Depends(get_db),
) -> List[Problem]:
    q = select(Problem).order_by(Problem.topic_id, Problem.difficulty, Problem.id)
    if topic_id:
        q = q.where(Problem.topic_id == topic_id)
    if difficulty:
        q = q.where(Problem.difficulty == difficulty)
    return list(db.scalars(q))


@router.get("/problems/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: int, db: Session = Depends(get_db)) -> Problem:
    return _get_or_404(db, Problem, problem_id, "Бодлого")


@router.post("/problems", response_model=ProblemOut, status_code=status.HTTP_201_CREATED)
def create_problem(data: ProblemIn, db: Session = Depends(get_db)) -> Problem:
    _ensure_topic(db, data.topic_id)
    problem = Problem(**data.model_dump())
    db.add(problem)
    _commit(db, f"'{data.code}' кодтой бодлого аль хэдийн байна")
    db.refresh(problem)
    return problem


@router.put("/problems/{problem_id}", response_model=ProblemOut)
def update_problem(problem_id: int, data: ProblemIn, db: Session = Depends(get_db)) -> Problem:
    problem = _get_or_404(db, Problem, problem_id, "Бодлого")
    _ensure_topic(db, data.topic_id)
    for k, v in data.model_dump().items():
        setattr(problem, k, v)
    _commit(db, f"'{data.code}' кодтой бодлого аль хэдийн байна")
    db.refresh(problem)
    return problem


@router.delete("/problems/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_problem(problem_id: int, db: Session = Depends(get_db)) -> Response:
    db.delete(_get_or_404(db, Problem, problem_id, "Бодлого"))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
