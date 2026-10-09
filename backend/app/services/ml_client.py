"""ML сервис (ml/service.py) рүү хандах клиент. ML ажиллахгүй үед систем зогсохгүй (NFR-07):
бүх функц алдааг залгиж None буцаана, дуудагч нь "гараар бичих" хувилбар руу шилжинэ."""

import logging
from typing import Optional

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


def _url(path: str) -> str:
    return settings.ml_service_url.rstrip("/") + path


def classify(text: str) -> Optional[dict]:
    """-> {"topic", "difficulty", "confidence", "subtopics"} | None"""
    if not settings.ml_service_url or not text.strip():
        return None
    try:
        r = httpx.post(_url("/classify"), json={"text": text}, timeout=settings.ml_timeout_seconds)
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001
        log.warning("ML classify амжилтгүй: %s", e)
        return None


def ocr(data: bytes, content_type: str) -> Optional[dict]:
    """-> {"text", "latex": [...]} | None"""
    if not settings.ml_service_url:
        return None
    try:
        r = httpx.post(
            _url("/ocr"),
            files={"file": ("image", data, content_type)},
            timeout=settings.ml_timeout_seconds,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001
        log.warning("ML OCR амжилтгүй: %s", e)
        return None


def health() -> dict:
    try:
        r = httpx.get(_url("/health"), timeout=3.0)
        r.raise_for_status()
        return {"available": True, **r.json()}
    except Exception:  # noqa: BLE001
        return {"available": False, "classifier": False, "ocr": False}
