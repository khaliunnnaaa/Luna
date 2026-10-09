"""Зургаас бодлого таних (NFR-05) — шинээр сургахгүй, бэлэн загваруудаар угсарсан pipeline.

  - Монгол текст: Tesseract + data/raw/tesseract/mon.traineddata
  - Томьёо:       pix2tex (LaTeX-OCR)

Алхам:
  1. Tesseract-аар үг бүрийн байрлалыг (bounding box) гаргана.
  2. Кирилл үсэг агуулсан үгсийг текст гэж, кириллгүй боловч тоо/латин/математикийн
     тэмдэгт агуулсан дараалсан үгсийг томьёоны муж гэж үзнэ.
  3. Томьёоны муж бүрийг тайрч pix2tex-д өгнө. Муж олдохгүй бол бүх зургийг өгнө.

Шаардлага:  pip install -r requirements-ocr.txt   ба   brew install tesseract
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

from ml.common import RAW_DIR

TESSDATA_DIR = RAW_DIR / "tesseract"
CYRILLIC = re.compile(r"[А-Яа-яЁёӨөҮү]")
MATHLIKE = re.compile(r"[0-9A-Za-z=+\-*/^()<>≤≥√π|]")
PAD = 6  # томьёоны мужийг тайрахдаа нэмэх зай (пиксел)


def _require(module: str, hint: str):
    try:
        return __import__(module)
    except ImportError as e:
        raise ImportError(f"`{module}` суугаагүй байна. {hint}") from e


@lru_cache(maxsize=1)
def _latex_model():
    """pix2tex загвар. Fine-tune хийсэн жин байвал орчны хувьсагчаар зааж өгнө:
         PIX2TEX_CHECKPOINT=models/pix2tex/weights.pth  PIX2TEX_CONFIG=models/pix2tex/config.yaml
       (Colab дээр сургасан жинг notebooks/ocr_colab.ipynb Drive-д хадгалдаг.)"""
    _require("pix2tex", "pip install -r requirements-ocr.txt")
    from pix2tex.cli import LatexOCR

    ckpt, cfg = os.environ.get("PIX2TEX_CHECKPOINT"), os.environ.get("PIX2TEX_CONFIG")
    if ckpt and cfg:
        from munch import Munch
        return LatexOCR(Munch({"config": cfg, "checkpoint": ckpt, "no_cuda": False, "no_resize": False}))
    return LatexOCR()


def _tesseract_config() -> str:
    if not (TESSDATA_DIR / "mon.traineddata").exists():
        raise FileNotFoundError(f"{TESSDATA_DIR / 'mon.traineddata'} алга. python download.py --only tesseract")
    return f'--tessdata-dir "{TESSDATA_DIR}" --psm 6'


def split_words(words: list[dict]) -> tuple[list[str], list[tuple[int, int, int, int]]]:
    """Tesseract-ийн үгсийг текстийн мөр ба томьёоны муж (x0, y0, x1, y1) болгон хуваана.
    words: [{"text", "line", "left", "top", "width", "height"}]  (line = мөрийн түлхүүр)"""
    lines: dict = {}
    regions: list[tuple[int, int, int, int]] = []
    current = None
    current_line = None
    for w in words:
        t = w["text"].strip()
        if not t:
            continue
        box = (w["left"], w["top"], w["left"] + w["width"], w["top"] + w["height"])
        is_math = not CYRILLIC.search(t) and MATHLIKE.search(t)
        if is_math:
            if current is not None and current_line == w["line"]:
                current = (min(current[0], box[0]), min(current[1], box[1]),
                           max(current[2], box[2]), max(current[3], box[3]))
            else:
                if current is not None:
                    regions.append(current)
                current, current_line = box, w["line"]
        else:
            if current is not None:
                regions.append(current)
                current = None
            lines.setdefault(w["line"], []).append(t)
    if current is not None:
        regions.append(current)
    return [" ".join(ws) for ws in lines.values()], regions


def recognize(path: str | Path) -> dict:
    """{"text": монгол текст, "latex": [томьёо, ...]}"""
    _require("PIL", "pip install Pillow")
    pytesseract = _require("pytesseract", "pip install pytesseract ба brew install tesseract")
    from PIL import Image

    img = Image.open(path).convert("RGB")
    data = pytesseract.image_to_data(img, lang="mon", config=_tesseract_config(),
                                     output_type=pytesseract.Output.DICT)
    words = [{"text": data["text"][i], "line": (data["block_num"][i], data["par_num"][i], data["line_num"][i]),
              "left": data["left"][i], "top": data["top"][i], "width": data["width"][i], "height": data["height"][i]}
             for i in range(len(data["text"]))]
    text_lines, regions = split_words(words)

    model = _latex_model()
    crops = [img.crop((max(0, x0 - PAD), max(0, y0 - PAD), min(img.width, x1 + PAD), min(img.height, y1 + PAD)))
             for x0, y0, x1, y1 in regions] or [img]
    latex = [model(c) for c in crops]
    return {"text": "\n".join(text_lines), "latex": latex}
