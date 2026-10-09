"""FR-08: Сэдэв бүрийн эзэмшлийг Bayesian Knowledge Tracing (BKT)-ээр хянах.

ML хэсгийн `ml/ml/tracing/mastery.py`-тэй ижил томьёо. Параметрийг `ml/config/bkt_params.yaml`-аас
уншина (ASSISTments дээр сургасан медиан утгууд); файл байхгүй бол доорх анхдагч утгыг хэрэглэнэ,
ингэснээр backend нь ML хавтасгүй ч ажиллана (NFR-07).

Төлөвийг ML хэсгийн JSON файлын оронд `mastery` хүснэгтэд хадгална.
"""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.learning import Mastery

EPS = 1e-4
# ml/config/bkt_params.yaml-ийн `default` хэсэгтэй ижил (2026-10-05-ны сургалт)
DEFAULT_PARAMS: Dict[str, float] = {
    "prior": 0.6673,
    "learn": 0.1431,
    "guess": 0.1463,
    "slip": 0.2316,
}

# Эзэмшсэн гэж үзэх босго — ML санал болгогчтой ижил
MASTERED = 0.95


@lru_cache(maxsize=1)
def load_bkt_params(path: Optional[str] = None) -> Dict[str, Dict[str, float]]:
    """{"default": {...}, "T01": {...}, ...}. YAML байхгүй/уншигдахгүй бол зөвхөн default."""
    params: Dict[str, Dict[str, float]] = {"default": dict(DEFAULT_PARAMS)}
    p = Path(path or settings.bkt_params_path)
    if not p.exists():
        return params
    try:
        import yaml  # pyyaml — requirements.txt-д бий

        cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 — буруу файл = анхдагч утга
        return params
    default = {**DEFAULT_PARAMS, **(cfg.get("default") or {})}
    params["default"] = default
    for code, vals in (cfg.get("topics") or {}).items():
        params[str(code)] = {**default, **(vals or {})}
    return params


def params_for(topic_id: str) -> Dict[str, float]:
    all_params = load_bkt_params()
    return all_params.get(topic_id, all_params["default"])


def bkt_update(p_mastery: float, correct: bool, learn: float, guess: float, slip: float) -> float:
    """Нэг хариултын дараах BKT шинэчлэл.

    1) Ажиглалтаар нөхцөлдүүлсэн магадлал:
         зөв:   p(1-s) / [p(1-s) + (1-p)g]
         буруу: p s    / [p s    + (1-p)(1-g)]
    2) Суралцах шилжилт: p' = post + (1 - post) * learn
    Үр дүнг [EPS, 1−EPS]-д хязгаарлана: яг 1.0 болбол буруу хариулт ч бууруулж чадахгүй гацна.
    """
    p = p_mastery
    if correct:
        post = p * (1 - slip) / (p * (1 - slip) + (1 - p) * guess)
    else:
        post = p * slip / (p * slip + (1 - p) * (1 - guess))
    return min(max(post + (1 - post) * learn, EPS), 1 - EPS)


def get_or_create(db: Session, user_id: int, topic_id: str) -> Mastery:
    m = db.get(Mastery, (user_id, topic_id))
    if m is None:
        m = Mastery(user_id=user_id, topic_id=topic_id, p_mastery=params_for(topic_id)["prior"])
        db.add(m)
        db.flush()
    return m


def record_answer(db: Session, user_id: int, topic_id: str, correct: bool) -> Mastery:
    """Хариултыг тооцож mastery-г шинэчилнэ (commit хийхгүй — дуудагч хийнэ)."""
    m = get_or_create(db, user_id, topic_id)
    p = params_for(topic_id)
    m.p_mastery = bkt_update(m.p_mastery, correct, p["learn"], p["guess"], p["slip"])
    m.attempts_count += 1
    if correct:
        m.correct_count += 1
    m.updated_at = datetime.now(timezone.utc)
    return m


def all_for_user(db: Session, user_id: int) -> Dict[str, Mastery]:
    rows = db.scalars(select(Mastery).where(Mastery.user_id == user_id))
    return {m.topic_id: m for m in rows}


def set_initial(db: Session, user_id: int, topic_id: str, p: float) -> Mastery:
    """FR-02 түвшин тогтоох тестийн үр дүнгээр анхны утгыг тавина."""
    m = get_or_create(db, user_id, topic_id)
    m.p_mastery = min(max(p, EPS), 1 - EPS)
    return m
