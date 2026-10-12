"""Зургийн урьдчилсан боловсруулалт: утасны камераар авсан зургийг OCR-д бэлдэх.

Алхам: EXIF эргэлт -> саарал -> хэмжээ тохируулах -> хазайлт засах -> гэрэлтүүлэг тэгшлэх.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageOps

# Tesseract нь мөрийн өндөр ~30-40px үед хамгийн сайн ажилладаг.
TARGET_MIN_WIDTH = 1200
TARGET_MAX_WIDTH = 2400


def load_image(data: bytes | str) -> np.ndarray:
    """bytes эсвэл файлын замаас зургийг BGR массив болгон уншина (EXIF эргэлтийг засна)."""
    if isinstance(data, (bytes, bytearray)):
        import io
        pil = Image.open(io.BytesIO(data))
    else:
        pil = Image.open(data)
    pil = ImageOps.exif_transpose(pil).convert("RGB")
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


TARGET_CHAR_H = 32   # Tesseract-д хамгийн тохиромжтой том үсгийн өндөр (px)


def estimate_char_height(gray: np.ndarray) -> float | None:
    """Connected component-уудын медиан өндрөөр үсгийн хэмжээг тооцно."""
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    n, _, st, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    if n < 6:
        return None
    hs = st[1:, cv2.CC_STAT_HEIGHT]
    ws = st[1:, cv2.CC_STAT_WIDTH]
    area = st[1:, cv2.CC_STAT_AREA]
    ok = (hs >= 4) & (area >= 12) & (ws < 4 * hs) & (hs < gray.shape[0] * 0.5)   # зураас, шуугиан, хүрээг хасна
    return float(np.median(hs[ok])) if ok.sum() >= 5 else None


def _resize(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Үсгийн өндрийг ~32px болгоно (зураг өргөнөөр биш, текстийн хэмжээгээр масштаблана)."""
    h, w = gray.shape
    ch = estimate_char_height(gray)
    if ch:
        s = float(np.clip(TARGET_CHAR_H / ch, 0.4, 4.0))
    elif w < TARGET_MIN_WIDTH:
        s = TARGET_MIN_WIDTH / w
    else:
        s = 1.0
    s = min(s, 4000 / max(w, h))            # хэт том зураг (санах ой, хурд — NFR-02)
    if abs(s - 1) < 0.15:
        return gray, 1.0
    interp = cv2.INTER_CUBIC if s > 1 else cv2.INTER_AREA
    return cv2.resize(gray, (int(w * s), int(h * s)), interpolation=interp), s


def _flatten_illumination(gray: np.ndarray) -> np.ndarray:
    """Утасны зурагт гардаг сүүдэр, жигд бус гэрлийг арилгана."""
    k = max(31, (min(gray.shape) // 20) | 1)
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    norm = cv2.divide(gray, bg, scale=255)
    return cv2.normalize(norm, None, 0, 255, cv2.NORM_MINMAX)


def _deskew(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Текстийн мөрийн өнцгийг олж, ±15° хүртэлх хазайлтыг засна."""
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    # Мөр болгон нэгтгэхийн тулд хэвтээ чиглэлд тэлнэ
    lines = cv2.dilate(bw, cv2.getStructuringElement(cv2.MORPH_RECT, (40, 3)))
    cnts, _ = cv2.findContours(lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    angles, weights = [], []
    for c in cnts:
        (_, _), (w, h), a = cv2.minAreaRect(c)
        if w < h:
            w, h, a = h, w, a - 90
        if w > 100 and w > 4 * h:
            if a > 45:
                a -= 90
            if a < -45:
                a += 90
            angles.append(a)
            weights.append(w)
    if not angles:
        return gray, 0.0
    angle = float(np.average(angles, weights=weights))
    if abs(angle) < 0.3 or abs(angle) > 15:
        return gray, 0.0
    h, w = gray.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=255), angle


def preprocess(img_bgr: np.ndarray) -> dict:
    """OCR-д бэлэн зураг буцаана.

    Returns:
        gray:   цэвэрлэсэн саарал зураг (томьёо таних загварт өгнө — pix2tex саарал зураг илүүд үздэг)
        binary: хар-цагаан (layout шинжилгээнд)
        angle:  зассан өнцөг
        scale:  анхны зурагтай харьцуулсан масштаб (bbox-ыг буцааж хөрвүүлэхэд)
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray, scale = _resize(gray)
    gray = _flatten_illumination(gray)
    gray, angle = _deskew(gray)
    gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    return {"gray": gray, "binary": binary, "angle": angle, "scale": scale}


def quality_report(gray: np.ndarray) -> dict:
    """Бүдэг/харанхуй зургийг эрт илрүүлж хэрэглэгчээс дахин авахыг хүсэх (FR-03 UX)."""
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean = float(gray.mean())
    issues = []
    if blur < 60:
        issues.append("Зураг бүдэг байна. Утсаа тогтвортой барьж дахин аваарай.")
    if mean < 90:
        issues.append("Зураг харанхуй байна. Гэрэлтэй газар дахин аваарай.")
    return {"sharpness": round(blur, 1), "brightness": round(mean, 1), "issues": issues}
