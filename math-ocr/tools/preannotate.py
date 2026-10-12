"""Шошголтыг хурдасгах: өөрсдийн авсан зургуудыг OCR-оор урьдчилан уншиж, ноорог шошго үүсгэнэ.
Хүн зөвхөн алдааг засна (300 зургийг 0-ээс бичихээс 3-4 дахин хурдан).

    python -m tools.preannotate --images data/real/images --out data/real/labels_draft.jsonl

Дараа нь labels_draft.jsonl-ийг нээж "markdown" ба formulas[].latex талбарыг засаад
labels.jsonl нэрээр хадгална. bbox буруу бол засах эсвэл тухайн "formulas" мөрийг устгана
(тэгвэл зөвхөн markdown-аар бүтэн pipeline үнэлэгдэнэ).
"""
from __future__ import annotations

import argparse
import glob
import json
import os

from ocr import MathOCR


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ocr = MathOCR()
    root = os.path.dirname(os.path.abspath(a.out))
    files = sorted(f for ext in ("jpg", "jpeg", "png", "webp") for f in glob.glob(os.path.join(a.images, f"*.{ext}")))
    with open(a.out, "w", encoding="utf-8") as f:
        for p in files:
            r = ocr(p)
            formulas = [{"latex": x["content"], "bbox": x["bbox"]} for line in r["lines"] for x in line if x["type"] == "formula"]
            f.write(json.dumps({"image": os.path.relpath(p, root).replace("\\", "/"), "markdown": r["markdown"],
                                "formulas": formulas, "_check": r["needs_review"]}, ensure_ascii=False) + "\n")
            print(os.path.basename(p), "->", r["markdown"].replace("\n", " / ")[:90])
    print(f"{len(files)} зураг -> {a.out}")


if __name__ == "__main__":
    main()
