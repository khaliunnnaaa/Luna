"""labels.jsonl-ийг train/val/test (70/15/15) болгож хуваах, pix2tex сургалтын формат үүсгэх.

    python -m tools.split_dataset --data data/real

Үүсгэнэ:
    labels_train.jsonl, labels_val.jsonl, labels_test.jsonl
    pix2tex/{train,val}/  — томьёоны тайрмал + math.txt (bbox-тэй шошгоос, эсвэл бүтэн зураг нэг томьёотой бол)

ЧУХАЛ: test багцыг зөвхөн эцсийн үнэлгээнд (NFR-05) ашиглана — fine-tune-д бүү оруул.
"""
from __future__ import annotations

import argparse
import json
import os
import random

import cv2

from eval.evaluate import split_markdown


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    items = [json.loads(l) for l in open(os.path.join(a.data, "labels.jsonl"), encoding="utf-8") if l.strip()]
    random.Random(a.seed).shuffle(items)
    n = len(items)
    parts = {"train": items[: int(n * 0.7)], "val": items[int(n * 0.7): int(n * 0.85)], "test": items[int(n * 0.85):]}
    for name, its in parts.items():
        with open(os.path.join(a.data, f"labels_{name}.jsonl"), "w", encoding="utf-8") as f:
            for it in its:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
    for name in ("train", "val"):
        out = os.path.join(a.data, "pix2tex", name)
        os.makedirs(out, exist_ok=True)
        k = 0
        with open(os.path.join(out, "math.txt"), "w", encoding="utf-8") as mf:
            for it in parts[name]:
                img = cv2.imread(os.path.join(a.data, it["image"]), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                boxes = it.get("formulas") or []
                if boxes and all("bbox" in b for b in boxes):
                    for b in boxes:
                        x1, y1, x2, y2 = b["bbox"]
                        cv2.imwrite(os.path.join(out, f"{k:07d}.png"), img[max(0, y1 - 4):y2 + 4, max(0, x1 - 4):x2 + 4])
                        mf.write(b["latex"] + "\n")
                        k += 1
                else:
                    _, fs = split_markdown(it["markdown"])
                    if len(fs) == 1 and not split_markdown(it["markdown"])[0]:   # зөвхөн томьёотой зураг
                        cv2.imwrite(os.path.join(out, f"{k:07d}.png"), img)
                        mf.write(fs[0] + "\n")
                        k += 1
        print(f"{name}: {len(parts[name])} зураг, {k} томьёоны тайрмал -> {out}")
    print(f"test: {len(parts['test'])} зураг (зөвхөн үнэлгээнд)")


if __name__ == "__main__":
    main()
