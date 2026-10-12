"""Томьёо таних: тайрсан томьёоны зураг -> LaTeX.

Үндсэн загвар: pix2tex (LaTeX-OCR). Өөрсдийн ≥300 зургийн багцаар fine-tune хийсэн
checkpoint-ийг `PIX2TEX_CHECKPOINT` орчны хувьсагчаар зааж ачаална.

pix2tex суулгаагүй / ачаалж чадаагүй үед Tesseract-ын уншсан тэмдэгтээс ойролцоо LaTeX
гаргаж, `needs_review=True` гэж тэмдэглэнэ (NFR-07: систем бүхэлдээ зогсохгүй).
"""
from __future__ import annotations

import logging
import os
import threading

import numpy as np
from PIL import Image

from .latex_utils import clean_latex, plausibility, unicode_to_latex

log = logging.getLogger(__name__)


class FormulaRecognizer:
    _lock = threading.Lock()        # загвар ачаалах
    _infer_lock = threading.Lock()  # LatexOCR нь дотоод төлөвтэй (last_pic г.м.) — зэрэг дуудахгүй

    def __init__(self, checkpoint: str | None = None, config: str | None = None):
        self.checkpoint = checkpoint or os.getenv("PIX2TEX_CHECKPOINT")
        self.config = config or os.getenv("PIX2TEX_CONFIG")
        self._model = None
        self._load_error: str | None = None

    @property
    def available(self) -> bool:
        self._ensure()
        return self._model is not None

    def _ensure(self) -> None:
        if self._model is not None or self._load_error is not None:
            return
        with self._lock:
            if self._model is not None or self._load_error is not None:
                return
            try:
                from pix2tex.cli import LatexOCR
                if self.checkpoint:
                    from munch import Munch
                    args = Munch({"config": self.config or "settings/config.yaml",
                                  "checkpoint": self.checkpoint, "no_cuda": True, "no_resize": False})
                    self._model = LatexOCR(args)
                else:
                    self._model = LatexOCR()      # анхны жинг автоматаар татна
                log.info("pix2tex ачааллаа (checkpoint=%s)", self.checkpoint or "default")
            except Exception as e:  # pragma: no cover
                self._load_error = f"{type(e).__name__}: {e}"
                log.warning("pix2tex ачаалж чадсангүй, fallback ашиглана: %s", self._load_error)

    @staticmethod
    def _prepare(crop: np.ndarray) -> Image.Image:
        """pix2tex цагаан дэвсгэртэй, бага зэрэг захтай зураг илүүд үздэг."""
        pad = max(6, crop.shape[0] // 8)
        crop = np.pad(crop, pad, constant_values=255)
        return Image.fromarray(crop).convert("RGB")

    def recognize(self, crop_gray: np.ndarray, fallback_text: str = "") -> dict:
        self._ensure()
        if self._model is not None:
            try:
                with self._infer_lock:
                    raw = self._model(self._prepare(crop_gray))
                latex = clean_latex(raw)
                conf = plausibility(latex)
                return {"latex": latex, "conf": conf, "engine": "pix2tex", "needs_review": conf < 0.7}
            except Exception as e:  # pragma: no cover
                log.warning("pix2tex алдаа: %s", e)
        latex = unicode_to_latex(fallback_text)
        return {"latex": latex, "conf": 0.3 if latex else 0.0, "engine": "fallback", "needs_review": True}
