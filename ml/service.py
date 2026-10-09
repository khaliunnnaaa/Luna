"""ML HTTP сервис — backend нь ML хэсгийг зөвхөн үүгээр дуудна (docs/architecture.md: API → ML service).

    .venv/bin/uvicorn service:app --port 8001            # локал
    docker compose up ml                                  # docker (порт 8001)

Endpoint:
    GET  /health            {"status": "ok", "classifier": true, "ocr": true/false}
    POST /classify          {"text": "..."} → {"topic", "difficulty", "confidence", "subtopics": [...]}
    POST /ocr               multipart "file" (jpg/png) → {"text": "...", "latex": [...]}

OCR нь Tesseract + pix2tex (torch) шаарддаг — суугаагүй бол /ocr 503 буцаана, backend гараар
бичих хувилбар руу шилжинэ (NFR-07). Ангилагч `models/*.joblib` байхгүй бол /classify 503.
"""
from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ml.common import MODELS_DIR

app = FastAPI(title="Ухаалаг математик — ML сервис")

MAX_IMAGE_BYTES = 10 * 1024 * 1024


class ClassifyIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def _classifier_ready() -> bool:
    return all((MODELS_DIR / f"{k}.joblib").exists() for k in ("topic_clf", "difficulty_clf", "subtopic_knn"))


def _ocr_ready() -> bool:
    return (
        importlib.util.find_spec("pix2tex") is not None
        and importlib.util.find_spec("pytesseract") is not None
        and shutil.which("tesseract") is not None
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "classifier": _classifier_ready(), "ocr": _ocr_ready()}


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
async def ocr(file: UploadFile = File(...)) -> dict:
    if not _ocr_ready():
        raise HTTPException(503, "OCR бэлэн биш: tesseract / pix2tex суугаагүй")
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(415, "Зөвхөн JPG/PNG зураг")
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Зураг 10 MB-аас их байна")
    suffix = ".png" if file.content_type == "image/png" else ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = Path(tmp.name)
    try:
        from ml.ocr.pipeline import recognize

        return recognize(path)
    finally:
        path.unlink(missing_ok=True)
