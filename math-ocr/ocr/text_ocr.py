"""Монгол (кирилл) текст таних — Tesseract `mon` загвар.

Tesseract-аас үг бүрийн байрлал (bbox), итгэлцүүр (conf)-ийг авна.
Энэ мэдээллийг layout.py ашиглан аль үг нь текст, аль нь томьёо болохыг ялгана.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytesseract


@dataclass
class Word:
    text: str
    conf: float          # 0..100, Tesseract-ийн итгэлцүүр
    x: int
    y: int
    w: int
    h: int
    line_id: tuple       # (block, paragraph, line) — нэг мөрийн үгсийг бүлэглэх

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h


def available_langs() -> set[str]:
    try:
        return set(pytesseract.get_languages(config=""))
    except Exception:
        return set()


def pick_lang(preferred: str = "mon+eng") -> str:
    """mon суулгаагүй бол eng рүү буцна (NFR-07: систем зогсохгүй)."""
    have = available_langs()
    langs = [l for l in preferred.split("+") if l in have]
    return "+".join(langs) if langs else "eng"


def ocr_words(gray: np.ndarray, lang: str | None = None, psm: int = 6) -> list[Word]:
    """Зургаас үг бүрийг байрлалтай нь уншина.

    psm 6 = нэг жигд текстийн блок (бодлогын зурагт тохиромжтой).
    preserve_interword_spaces нь томьёоны доторх зайг хадгална.
    """
    lang = lang or pick_lang()
    cfg = f"--oem 1 --psm {psm} -c preserve_interword_spaces=1"
    d = pytesseract.image_to_data(gray, lang=lang, config=cfg, output_type=pytesseract.Output.DICT)
    words: list[Word] = []
    for i, t in enumerate(d["text"]):
        t = (t or "").strip()
        if not t:
            continue
        words.append(Word(
            text=t,
            conf=float(d["conf"][i]),
            x=int(d["left"][i]), y=int(d["top"][i]), w=int(d["width"][i]), h=int(d["height"][i]),
            line_id=(d["block_num"][i], d["par_num"][i], d["line_num"][i]),
        ))
    return words


def ocr_region_text(gray: np.ndarray, lang: str | None = None) -> tuple[str, float]:
    """Тайрсан хэсгийг нэг мөр гэж үзээд уншина (psm 7)."""
    words = ocr_words(gray, lang=lang, psm=7)
    if not words:
        return "", 0.0
    return " ".join(w.text for w in words), float(np.mean([w.conf for w in words]))
