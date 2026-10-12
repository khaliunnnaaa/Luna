"""OCR микро-үйлчилгээ (FastAPI) — FR-03, NFR-02, NFR-07.

    uvicorn api:app --host 0.0.0.0 --port 8001

POST /ocr        multipart зураг -> {markdown, lines[], needs_review, quality, timing_ms}
GET  /health     загварууд ачаалагдсан эсэх

Үндсэн backend (FastAPI) энэ үйлчилгээг дуудна. OCR унасан/удаасан үед backend
"гараар бичих" горим руу шилжинэ (NFR-07) — үүний тулд энд 503/504 тодорхой буцаана.
"""
from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, HTTPException, UploadFile

from ocr import MathOCR

logging.basicConfig(level=logging.INFO)
MAX_BYTES = 10 * 1024 * 1024                          # backend-ийн хязгаартай ижил
TIMEOUT_S = float(os.getenv("OCR_TIMEOUT_S", "8"))       # дотоод төсөв 5с + нөөц
ALLOWED = {"image/jpeg", "image/png", "image/webp"}   # HEIC-ийг Pillow pillow-heif-гүйгээр уншихгүй

app = FastAPI(title="Math OCR (Монгол + LaTeX)", version="0.1.0")

_ocr: MathOCR | None = None
_pool = ThreadPoolExecutor(max_workers=int(os.getenv("OCR_WORKERS", "2")))


@app.on_event("startup")
def _startup() -> None:
    global _ocr
    _ocr = MathOCR(time_budget_s=float(os.getenv("OCR_BUDGET_S", "5")))
    _ocr.warmup()


@app.get("/health")
def health() -> dict:
    if _ocr is None:
        raise HTTPException(503, "загвар ачаалагдаагүй")
    return {"ok": True, "text": _ocr.lang, "formula": "pix2tex" if _ocr.formula.available else "fallback",
            "detector": "mfd" if _ocr.mfd else "heuristic"}


@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)) -> dict:
    if _ocr is None:
        raise HTTPException(503, "OCR үйлчилгээ бэлэн биш. Бодлогоо гараар бичнэ үү.")
    if file.content_type and file.content_type not in ALLOWED:
        raise HTTPException(415, "Зөвхөн JPG, PNG, WEBP зураг оруулна уу.")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Зураг 10MB-аас ихгүй байх ёстой.")
    loop = asyncio.get_running_loop()
    try:
        # Зургийг дискэнд хадгалахгүй (NFR-06): зөвхөн санах ойд боловсруулна
        return await asyncio.wait_for(loop.run_in_executor(_pool, _ocr, data), timeout=TIMEOUT_S)
    except asyncio.TimeoutError:
        raise HTTPException(504, "Зураг таних хугацаа хэтэрлээ. Дахин оролдох эсвэл гараар бичнэ үү.")
    except Exception as e:  # pragma: no cover
        logging.exception("OCR алдаа")
        raise HTTPException(422, f"Зургийг уншиж чадсангүй: {type(e).__name__}")
