"""FR-14: эцэг эхийн самбар.

Холбох урсгал (NFR-06 — хүүхдийн зөвшөөрөлгүйгээр мэдээлэл харагдахгүй):
  сурагч  POST /me/link-code        → 6 тэмдэгт код (48 цаг, нэг удаагийн)
  эцэг эх POST /parent/children     {code} → холбогдоно, код устана
Сурагч өөрийг нь хэн харж байгааг /me/parents-аар харж, холбоог салгаж болно.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.models.learning import Attempt, LinkCode, ParentChildLink
from app.models.user import Role, User
from app.schemas.parent import LinkCodeOut, LinkIn, PersonOut, ReportOut
from app.services import mastery as mastery_svc
from app.services import placement as placement_svc
from app.services.parent_report import build_report

router = APIRouter(tags=["parent"])
student = Depends(require_role(Role.student))
parent = Depends(require_role(Role.parent))

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 0/O, 1/I андуурагдахгүй
CODE_TTL = timedelta(hours=48)
MAX_CHILDREN = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # SQLite naive


# ---------- Сурагч ----------
@router.post("/me/link-code", response_model=LinkCodeOut)
def create_link_code(db: Session = Depends(get_db), user: User = student):
    """Шинэ код үүсгэнэ; өмнөх код хүчингүй болно."""
    old = db.scalar(select(LinkCode).where(LinkCode.child_id == user.id))
    if old:
        db.delete(old)
        db.flush()
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
    lc = LinkCode(code=code, child_id=user.id, expires_at=_now() + CODE_TTL)
    db.add(lc)
    db.commit()
    return LinkCodeOut(code=code, expires_at=lc.expires_at)


@router.get("/me/parents", response_model=List[PersonOut])
def my_parents(db: Session = Depends(get_db), user: User = student):
    rows = db.scalars(
        select(User)
        .join(ParentChildLink, ParentChildLink.parent_id == User.id)
        .where(ParentChildLink.child_id == user.id)
        .order_by(User.full_name)
    )
    return [PersonOut(id=u.id, full_name=u.full_name) for u in rows]


@router.delete("/me/parents/{parent_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_parent(parent_id: int, db: Session = Depends(get_db), user: User = student):
    link = db.get(ParentChildLink, (parent_id, user.id))
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Холбоос олдсонгүй")
    db.delete(link)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Эцэг эх ----------
def _child_or_404(db: Session, parent_id: int, child_id: int) -> User:
    """Зөвхөн холбогдсон хүүхдийн мэдээлэл — бусдынхыг 404 (байгаа эсэхийг ч задруулахгүй)."""
    if db.get(ParentChildLink, (parent_id, child_id)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Хүүхэд олдсонгүй")
    return db.get(User, child_id)


@router.post("/parent/children", response_model=PersonOut)
def link_child(data: LinkIn, db: Session = Depends(get_db), user: User = parent):
    lc = db.get(LinkCode, data.code.strip().upper())
    if lc is None or _aware(lc.expires_at) < _now():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Код буруу эсвэл хугацаа нь дууссан байна. Хүүхдээсээ шинэ код аваарай.",
        )
    child = db.get(User, lc.child_id)
    if db.get(ParentChildLink, (user.id, child.id)) is None:
        count = len(
            db.scalars(select(ParentChildLink).where(ParentChildLink.parent_id == user.id)).all()
        )
        if count >= MAX_CHILDREN:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"{MAX_CHILDREN}-аас олон хүүхэд холбох боломжгүй",
            )
        db.add(ParentChildLink(parent_id=user.id, child_id=child.id))
    db.delete(lc)  # нэг удаагийн
    db.commit()
    return PersonOut(id=child.id, full_name=child.full_name)


@router.get("/parent/children", response_model=List[PersonOut])
def my_children(db: Session = Depends(get_db), user: User = parent):
    rows = db.scalars(
        select(User)
        .join(ParentChildLink, ParentChildLink.child_id == User.id)
        .where(ParentChildLink.parent_id == user.id)
        .order_by(User.full_name)
    )
    return [PersonOut(id=u.id, full_name=u.full_name) for u in rows]


@router.delete("/parent/children/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_child(child_id: int, db: Session = Depends(get_db), user: User = parent):
    _child_or_404(db, user.id, child_id)
    db.delete(db.get(ParentChildLink, (user.id, child_id)))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/parent/children/{child_id}/report", response_model=ReportOut)
def child_report(child_id: int, db: Session = Depends(get_db), user: User = parent):
    child = _child_or_404(db, user.id, child_id)
    attempts = db.scalars(
        select(Attempt).where(Attempt.user_id == child.id).order_by(Attempt.created_at)
    ).all()
    first_name = child.full_name.strip().split()[-1] if child.full_name.strip() else "Хүүхэд"
    report = build_report(
        child_name=first_name,
        attempts=attempts,
        mastery=mastery_svc.overview(db, child.id),
        now=_now(),
        placement_done=placement_svc.last_done(db, child.id) is not None,
    )
    return ReportOut(child=PersonOut(id=child.id, full_name=child.full_name), **report)
