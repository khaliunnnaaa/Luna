"""FR-03: бодлогын зураг оруулах → OCR → засварлах. FR-04: сэдэв ангилах.

ML сервис унтарсан үед (NFR-07): зураг хадгалагдана, status=failed, сурагч текстээ гараар бичнэ;
`POST /classify` нь ML-гүй бол available=false буцаана, UI сэдвээ өөрөө сонгуулна.
"""

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.content import Term, Topic
from app.models.learning import Upload
from app.models.user import User
from app.schemas.uploads import (
    ClassifyIn,
    ClassifyOut,
    OutcomeIn,
    SimilarIn,
    SimilarOut,
    UploadDetailOut,
    UploadEditIn,
    UploadOut,
)
from app.services import ml_client, similar, storage

router = APIRouter(tags=["uploads"])

ALLOWED = {"image/jpeg", "image/png"}
MSG_OK = "Текстийг шалгаад, буруу танигдсан бол засаарай."
MSG_NO_ML = "Зураг таних үйлчилгээ одоогоор ажиллахгүй байна. Бодлогоо гараар бичээрэй."


def _matched_terms(db: Session, text: str) -> List[str]:
    low = text.lower()
    return [t.term for t in db.scalars(select(Term)) if t.term.lower() in low]


def _classify_out(db: Session, text: str) -> ClassifyOut:
    r = ml_client.classify(text)
    terms = _matched_terms(db, text)
    if r is None:
        return ClassifyOut(available=False, terms=terms)
    topic = db.get(Topic, r.get("topic"))
    return ClassifyOut(
        available=True,
        topic_id=r.get("topic"),
        topic_name=topic.name if topic else r.get("topic"),
        difficulty=r.get("difficulty"),
        confidence=r.get("confidence"),
        subtopics=r.get("subtopics") or [],
        terms=terms,
    )


def _mine_or_404(db: Session, upload_id: int, user: User) -> Upload:
    u = db.get(Upload, upload_id)
    if u is None or u.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Зураг олдсонгүй")
    return u


def _detail(db: Session, u: Upload, ml_available: bool, message: str) -> UploadDetailOut:
    topic = db.get(Topic, u.predicted_topic) if u.predicted_topic else None
    return UploadDetailOut(
        **UploadOut.model_validate(u).model_dump(),
        topic_name=topic.name if topic else None,
        ml_available=ml_available,
        message=message,
    )


@router.post("/classify", response_model=ClassifyOut)
def classify_text(
    data: ClassifyIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> ClassifyOut:
    """FR-04: гараар бичсэн эсвэл засварласан бодлогын сэдвийг тодорхойлно."""
    return _classify_out(db, data.text)


@router.post("/uploads", response_model=UploadDetailOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadDetailOut:
    """FR-03: зураг хадгалаад OCR + ангилал хийнэ. ML-гүй бол status=failed, текст хоосон."""
    if file.content_type not in ALLOWED:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Зөвхөн JPG эсвэл PNG зураг"
        )
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Хоосон файл")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Зураг 10 MB-аас их байна"
        )

    key = storage.new_key(user.id, file.content_type)
    storage.get_storage().save(key, data, file.content_type)
    u = Upload(user_id=user.id, object_key=key, status="pending")
    db.add(u)
    db.flush()

    ocr = ml_client.ocr(data, file.content_type)
    if ocr is None:
        u.status = "failed"
        db.commit()
        db.refresh(u)
        return _detail(db, u, ml_available=False, message=MSG_NO_ML)

    u.ocr_text = (ocr.get("text") or "").strip()
    u.ocr_latex = " ".join(ocr.get("latex") or []).strip() or None
    full = " ".join(s for s in (u.ocr_text, u.ocr_latex) if s)
    u.edited_text = full or None
    c = ml_client.classify(full) if full else None
    u.predicted_topic = c.get("topic") if c else None
    u.status = "done"
    db.commit()
    db.refresh(u)
    return _detail(db, u, ml_available=True, message=MSG_OK)


@router.get("/uploads", response_model=List[UploadOut])
def my_uploads(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(
        db.scalars(select(Upload).where(Upload.user_id == user.id).order_by(Upload.id.desc()))
    )


@router.get("/uploads/{upload_id}", response_model=UploadDetailOut)
def get_upload(
    upload_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    u = _mine_or_404(db, upload_id, user)
    return _detail(db, u, ml_available=u.status != "failed", message="")


@router.get("/uploads/{upload_id}/image")
def get_upload_image(
    upload_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    """Зургийг зөвхөн эзэмшигчид нь харуулна (NFR-06)."""
    u = _mine_or_404(db, upload_id, user)
    data = storage.get_storage().load(u.object_key)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Зургийн файл олдсонгүй")
    media = "image/png" if u.object_key.endswith(".png") else "image/jpeg"
    return Response(content=data, media_type=media)


@router.put("/uploads/{upload_id}", response_model=UploadDetailOut)
def edit_upload(
    upload_id: int,
    data: UploadEditIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadDetailOut:
    """Сурагч OCR-ийн текстийг засаад (эсвэл гараар бичээд) дахин ангилуулна."""
    u = _mine_or_404(db, upload_id, user)
    u.edited_text = data.edited_text.strip()
    c = ml_client.classify(u.edited_text)
    u.predicted_topic = c.get("topic") if c else u.predicted_topic
    if u.status == "failed" and u.edited_text:
        u.status = "done"  # гараар бичсэн → ашиглах боломжтой
    db.commit()
    db.refresh(u)
    return _detail(db, u, ml_available=c is not None, message="" if c else MSG_NO_ML)


@router.delete("/uploads/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(
    upload_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    """NFR-06: хэрэглэгч оруулсан зургаа устгах боломжтой — файл ба бичлэг хоёулаа."""
    u = _mine_or_404(db, upload_id, user)
    storage.get_storage().delete(u.object_key)
    db.delete(u)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================= FR-07: ижил төстэй бодлогоор тайлбарлах =================
@router.post("/similar", response_model=SimilarOut)
def similar_problem(
    data: SimilarIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SimilarOut:
    """Сурагчийн бодлогын оронд ижил төрлийн бодлогыг алхамчилсан бодолттой нь өгнө.

    Систем сурагчийн өөрийн бодлогыг бодохгүй (FR-06) — жишээг хамт бодсоны дараа сурагч
    өөрийнхөө бодлогыг бие даан бодно.
    """
    c = ml_client.classify(data.text) if data.text.strip() else None
    topic_id = data.topic_id or (c.get("topic") if c else None)
    if not topic_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Сэдвийг тодорхойлж чадсангүй — сэдвээ сонгоно уу",
        )
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Сэдэв олдсонгүй")
    p = similar.find_similar(
        db,
        user.id,
        topic_id,
        difficulty=c.get("difficulty") if c else None,
        subtopics=c.get("subtopics") if c else None,
        exclude=data.exclude,
    )
    if p is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Энэ сэдэвт бодолттой жишээ бодлого алга"
        )
    reason = f"{topic.name} сэдвийн"
    if p.subtopic:
        reason += f" «{p.subtopic}» төрлийн"
    reason += " жишээ. Алхмуудыг нэг нэгээр нь нээж, дараа нь өөрийнхөө бодлогыг бод."
    return SimilarOut(
        topic_id=topic_id,
        topic_name=topic.name,
        problem_id=p.id,
        code=p.code,
        subtopic=p.subtopic,
        difficulty=p.difficulty,
        statement=p.statement,
        terms=p.terms or [],
        steps=p.solution_steps,
        reason=reason,
        ml_available=c is not None,
    )


@router.post("/uploads/{upload_id}/outcome", response_model=UploadDetailOut)
def set_outcome(
    upload_id: int,
    data: OutcomeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadDetailOut:
    """FR-07: жишээг үзсэний дараа сурагч өөрийн бодлогоо бодож чадсан эсэхээ тэмдэглэнэ."""
    u = _mine_or_404(db, upload_id, user)
    u.outcome = "solved" if data.solved else "unsolved"
    db.commit()
    db.refresh(u)
    return _detail(db, u, ml_available=True, message="")


@router.get("/ml/health")
def ml_health() -> dict:
    """UI-д: зураг оруулах товчийг идэвхтэй/идэвхгүй болгоход."""
    return ml_client.health()
