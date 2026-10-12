"""ML HTTP сервис — backend нь ML хэсгийг зөвхөн үүгээр дуудна (docs/architecture.md: API → ML service).

    .venv/bin/uvicorn service:app --port 8001            # локал
    docker compose up ml                                  # docker (порт 8001)

Endpoint:
    GET  /health            {"status": "ok", "classifier": true, "ocr": true/false, "ocr_engines": {...}}
    POST /classify          {"text": "..."} → {"topic", "difficulty", "confidence", "subtopics": [...]}
    POST /ocr               multipart "file" (jpg/png) → {"text", "latex": [...], "markdown",
                            "needs_review", "quality": {"issues": [...]}, "timing_ms"}

OCR = `math-ocr/` модуль (Tesseract mon + layout + pix2tex). Загвар сервер асахад арын thread-д
ачаалагдана (эхний удаа pix2tex жин ~115MB татна); бэлэн болтол /ocr 503 буцааж, backend гараар
бичих хувилбар руу шилжинэ (NFR-07). Ангилагч `models/*.joblib` байхгүй бол /classify 503.
"""
from __future__ import annotations

import logging
import os
import shutil
import sys
import threading
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ml.common import MODELS_DIR

log = logging.getLogger(__name__)
app = FastAPI(title="Ухаалаг математик — ML сервис")

MAX_IMAGE_BYTES = 10 * 1024 * 1024

# math-ocr/ хавтас (repo-гийн үндсэнд; docker-д MATH_OCR_DIR-ээр заана)
MATH_OCR_DIR = Path(os.getenv("MATH_OCR_DIR", Path(__file__).resolve().parent.parent / "math-ocr"))
_ocr = None  # MathOCR — арын thread-д ачаалагдана
_ocr_error: str | None = None


def _load_ocr() -> None:
    global _ocr, _ocr_error
    try:
        if shutil.which("tesseract") is None:
            raise RuntimeError("tesseract суугаагүй (brew install tesseract tesseract-lang)")
        if str(MATH_OCR_DIR) not in sys.path:
            sys.path.insert(0, str(MATH_OCR_DIR))
        from ocr import MathOCR

        m = MathOCR(time_budget_s=float(os.getenv("OCR_BUDGET_S", "5")))
        m.warmup()  # pix2tex ачаалж, эхний хүсэлт удаан болохоос сэргийлнэ
        _ocr = m
        log.info("OCR бэлэн: tesseract:%s, formula=%s", m.lang, "pix2tex" if m.formula.available else "fallback")
    except Exception as e:  # noqa: BLE001
        _ocr_error = f"{type(e).__name__}: {e}"
        log.warning("OCR ачаалж чадсангүй (гараар бичих горим): %s", _ocr_error)


@app.on_event("startup")
def _startup() -> None:
    threading.Thread(target=_load_ocr, daemon=True).start()


class ClassifyIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def _classifier_ready() -> bool:
    return all((MODELS_DIR / f"{k}.joblib").exists() for k in ("topic_clf", "difficulty_clf", "subtopic_knn"))


def _ocr_ready() -> bool:
    return _ocr is not None


@app.get("/health")
def health() -> dict:
    engines = None
    if _ocr is not None:
        engines = {"text": f"tesseract:{_ocr.lang}", "formula": "pix2tex" if _ocr.formula.available else "fallback"}
    return {"status": "ok", "classifier": _classifier_ready(), "ocr": _ocr_ready(),
            "ocr_engines": engines, "ocr_error": _ocr_error}


@app.post("/classify")
def classify(data: ClassifyIn) -> dict:
    if not _classifier_ready():
        raise HTTPException(503, "Ангилагчийн загвар алга (python -m ml.classifier.train)")
    from ml.classifier.predict import predict, suggest_subtopics

    r = predict(data.text)
    return {
        "topic": r["topic"],
        "difficulty": r["difficulty"],
        "confidence": r["confidence"],
        "subtopics": suggest_subtopics(data.text, r["topic"]),
    }


@app.post("/ocr")
def ocr(file: UploadFile = File(...)) -> dict:
    # sync def: FastAPI threadpool-д ажиллуулна — удаан OCR event loop-ыг (/health, /classify) гацаахгүй
    if _ocr is None:
        raise HTTPException(503, "OCR бэлэн биш" + (f": {_ocr_error}" if _ocr_error else " (ачаалж байна)"))
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(415, "Зөвхөн JPG/PNG зураг")
    data = file.file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Зураг 10 MB-аас их байна")
    try:
        # Зургийг дискэнд хадгалахгүй, санах ойд боловсруулна (NFR-06)
        r = _ocr(data)
    except Exception as e:  # noqa: BLE001
        log.exception("OCR алдаа")
        raise HTTPException(422, f"Зургийг уншиж чадсангүй: {type(e).__name__}") from e
    regions = [x for line in r["lines"] for x in line]
    return {
        "text": " ".join(x["content"] for x in regions if x["type"] == "text"),
        "latex": [x["content"] for x in regions if x["type"] == "formula"],
        # frontend-ийн MathText зөвхөн $...$ таньдаг тул $$...$$-ийг нэгтгэнэ
        "markdown": r["markdown"].replace("$$", "$"),
        "needs_review": r["needs_review"],
        "quality": r["quality"],
        "engines": r["engines"],
        "timing_ms": r["timing_ms"],
    }
