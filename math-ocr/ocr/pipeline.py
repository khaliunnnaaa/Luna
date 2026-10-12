"""Бодлогын зураг -> {текст + LaTeX} бүтэцтэй үр дүн (FR-03).

    from ocr import MathOCR
    ocr = MathOCR()
    res = ocr(open("bodlogo.jpg", "rb").read())
    print(res["markdown"])   # "Тэгшитгэлийг бод: $x^{2}-5x+6=0$"

Үр дүнг frontend дээр KaTeX-ээр харуулж, сурагч засварлах боломжтой (needs_review бүсийг тодруулна).
"""
from __future__ import annotations

import logging
import os
import time

import numpy as np

from .formula_ocr import FormulaRecognizer
from .layout import MFDDetector, Region, order_into_lines, segment
from .preprocess import load_image, preprocess, quality_report
from .text_ocr import ocr_words, pick_lang
from .text_post import postprocess_text

log = logging.getLogger(__name__)


class MathOCR:
    def __init__(self, lang: str = "mon+eng", mfd_onnx: str | None = None, formula: FormulaRecognizer | None = None,
                 time_budget_s: float = 5.0):
        self.lang = pick_lang(lang)
        if self.lang != lang:
            log.warning("Tesseract '%s' хэл олдсонгүй, '%s' ашиглана", lang, self.lang)
        self.formula = formula or FormulaRecognizer()
        mfd_onnx = mfd_onnx or os.getenv("MFD_ONNX")
        self.mfd = MFDDetector(mfd_onnx) if mfd_onnx and os.path.exists(mfd_onnx) else None
        self.time_budget_s = time_budget_s           # NFR-02: 5 секунд

    def warmup(self) -> None:
        """Сервер асахад загваруудыг ачаална — эхний хүсэлт удаан болохоос сэргийлнэ."""
        self.formula.available
        self(np.full((80, 400, 3), 255, np.uint8))

    def __call__(self, image: bytes | str | np.ndarray) -> dict:
        t0 = time.perf_counter()
        img = image if isinstance(image, np.ndarray) else load_image(image)
        import cv2
        raw_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        quality = quality_report(raw_gray)
        pre = preprocess(img if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
        gray, binary = pre["gray"], pre["binary"]
        t_pre = time.perf_counter()

        words = ocr_words(gray, lang=self.lang)
        mfd_boxes = self.mfd(gray) if self.mfd else None
        regions = segment(words, binary, mfd_boxes)
        t_seg = time.perf_counter()

        timed_out = False
        for r in regions:
            if r.kind == "text":
                r.content = postprocess_text(" ".join(w.text for w in r.words))
                r.conf = float(np.mean([w.conf for w in r.words])) / 100 if r.words else 0.0
                r.needs_review = r.conf < 0.6
            else:
                fallback = " ".join(w.text for w in sorted(r.words, key=lambda w: (w.y, w.x)))
                if time.perf_counter() - t0 > self.time_budget_s:
                    # Хугацаа хэтэрвэл үлдсэн томьёог хурдан fallback-аар бөглөж, засварлуулна
                    from .latex_utils import unicode_to_latex
                    r.content, r.conf, r.needs_review, timed_out = unicode_to_latex(fallback), 0.2, True, True
                    continue
                pad = 4
                crop = gray[max(0, r.y - pad): r.y2 + pad, max(0, r.x - pad): r.x2 + pad]
                res = self.formula.recognize(crop, fallback_text=fallback)
                r.content, r.conf, r.needs_review = res["latex"], res["conf"], res["needs_review"]
        t_end = time.perf_counter()

        lines = order_into_lines(regions)
        sc = pre["scale"]
        return {
            "markdown": to_markdown(lines),
            # bbox нь анхны зургийн координатаар (frontend дээр тодруулж харуулахад)
            "lines": [[region_dict(r, sc) for r in line] for line in lines],
            "needs_review": any(r.needs_review for r in regions),
            "quality": quality,
            "engines": {"text": f"tesseract:{self.lang}",
                        "formula": "pix2tex" if self.formula.available else "fallback",
                        "detector": "mfd" if self.mfd else "heuristic"},
            "timing_ms": {"preprocess": round((t_pre - t0) * 1000), "layout": round((t_seg - t_pre) * 1000),
                          "recognize": round((t_end - t_seg) * 1000), "total": round((t_end - t0) * 1000)},
            "timed_out": timed_out,
        }


def region_dict(r: Region, scale: float = 1.0) -> dict:
    return {"type": r.kind, "content": r.content, "bbox": [int(round(int(v) / scale)) for v in r.box()],
            "conf": round(float(r.conf), 2),
            "needs_review": r.needs_review}


def to_markdown(lines: list[list[Region]]) -> str:
    """Текстийг энгийнээр, томьёог $...$ (мөрөнд ганцаараа бол $$...$$) болгож нэгтгэнэ."""
    out = []
    for line in lines:
        if len(line) == 1 and line[0].kind == "formula":
            out.append(f"$${line[0].content}$$")
            continue
        parts = []
        for r in line:
            parts.append(f"${r.content}$" if r.kind == "formula" else r.content)
        s = " ".join(p for p in parts if p)
        out.append(s.replace(" .", ".").replace(" ,", ",").replace(" :", ":"))
    return "\n".join(out)
