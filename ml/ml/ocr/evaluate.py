"""OCR-ийн үнэлгээ (NFR-05: ≥ 85%).

Өгөгдлийн формат: data/own_images/ хавтсанд зураг (png/jpg/jpeg) ба ижил нэртэй .tex файл
(жинхэнэ LaTeX), жишээ нь  T04-021.jpg  +  T04-021.tex

Метрик (LaTeX-ийг хэвийн болгосны дараа):
  - exact match: таамаг жинхэнэтэй яг ижил байх хувь
  - normalized edit distance (NED): Левенштейн зай / урт-ын их нь;  1 − NED = тэмдэгтийн нарийвчлал

Ажиллуулах:  python -m ml.ocr.evaluate
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ml.common import REPORTS_DIR, ROOT
from ml.report import update_section

IMAGES_DIR = ROOT / "data" / "own_images"
IMAGE_EXT = {".png", ".jpg", ".jpeg"}
TARGET = 0.85


def normalize_latex(s: str) -> str:
    s = s.strip().strip("$")
    s = re.sub(r"\\(left|right|displaystyle|textstyle)\b", "", s)
    s = re.sub(r"\\[dt]frac", r"\\frac", s)
    s = re.sub(r"\\[,;:! ]|~", "", s)          # зайн командууд
    s = s.replace("\\cdot", "·").replace("\\times", "×")
    s = re.sub(r"\{\s*([A-Za-z0-9])\s*\}", r"\1", s)  # {x} -> x
    return re.sub(r"\s+", "", s)


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def normalized_edit_distance(pred: str, true: str) -> float:
    p, t = normalize_latex(pred), normalize_latex(true)
    if not p and not t:
        return 0.0
    return levenshtein(p, t) / max(len(p), len(t))


def find_pairs(directory: Path = IMAGES_DIR) -> list[tuple[Path, str]]:
    if not directory.exists():
        return []
    pairs = []
    for img in sorted(directory.iterdir()):
        tex = img.with_suffix(".tex")
        if img.suffix.lower() in IMAGE_EXT and tex.exists():
            pairs.append((img, tex.read_text(encoding="utf-8").strip()))
    return pairs


def score(preds: list[str], truths: list[str]) -> dict:
    neds = [normalized_edit_distance(p, t) for p, t in zip(preds, truths)]
    exact = [normalize_latex(p) == normalize_latex(t) for p, t in zip(preds, truths)]
    n = len(truths)
    return {"n": n, "exact_match": sum(exact) / n, "mean_ned": sum(neds) / n, "char_accuracy": 1 - sum(neds) / n}


def main():
    pairs = find_pairs()
    if not pairs:
        msg = (f"## 4. OCR (NFR-05: ≥ {TARGET:.0%})\n\n**Өгөгдөл хүлээж байна.** `data/own_images/`-д зураг ↔ `.tex` хос "
               "олдсонгүй. Үнэлгээний скрипт (`ml/ocr/evaluate.py`) бэлэн: зураг бүрийн хажууд ижил нэртэй `.tex` "
               "файл (жинхэнэ LaTeX) тавиад `python -m ml.ocr.evaluate` ажиллуулна. Метрик: exact match ба "
               "normalized edit distance (хэвийн болгосон LaTeX дээр).")
        update_section("ocr", msg)
        print("data/own_images/-д хос алга — өгөгдөл хүлээж байна.")
        return
    from ml.ocr.pipeline import recognize

    preds = []
    for img, _ in pairs:
        latex = recognize(img)["latex"]
        preds.append(" ".join(latex))
    result = score(preds, [t for _, t in pairs])
    REPORTS_DIR.mkdir(exist_ok=True)
    (REPORTS_DIR / "ocr_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    ok = lambda v: "✅" if v >= TARGET else "❌"  # noqa: E731
    update_section("ocr", f"""## 4. OCR (NFR-05: ≥ {TARGET:.0%})

{result['n']} зураг (data/own_images/), pix2tex + Tesseract (mon).

| Метрик | Утга | Зорилт |
|---|---|---|
| Exact match | {result['exact_match']:.3f} | {ok(result['exact_match'])} ≥ {TARGET} |
| 1 − NED (тэмдэгтийн нарийвчлал) | {result['char_accuracy']:.3f} | {ok(result['char_accuracy'])} ≥ {TARGET} |
| Mean NED | {result['mean_ned']:.3f} | |
""")
    print(result)


if __name__ == "__main__":
    main()
