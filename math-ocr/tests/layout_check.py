"""Layout (текст/томьёо ялгах) шалгалт синтетик зураг дээр.

    python -m tests.layout_check --n 40          # mon суулгасан бол монгол текстээр
    python -m tests.layout_check --n 40 --en     # зөвхөн eng байгаа орчинд англи текстээр

Томьёоны хүрээ GT-тэй IoU > 0.5 бөгөөд яг 1 томьёо олдсон бол "зөв" гэж тооцно.
"""
from __future__ import annotations

import argparse
import random
import re

import cv2
import numpy as np

import ocr.layout as L
import tools.synth as S
from ocr import MathOCR

EN = {"Тэгшитгэлийг бод:": "Solve the equation:", "Тэнцэтгэл бишийг бод:": "Solve the inequality:",
      "Илэрхийллийг хялбарчил:": "Simplify the expression:", "Утгыг ол:": "Find the value:",
      "Тооцоол:": "Compute:", "Функцийн тодорхойлогдох мужийг ол:": "Find the domain:", "Хэрэв": "If",
      "Магадлалыг ол:": "Find probability:"}


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / u if u else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--en", action="store_true")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    if a.en:
        L.RE_MN_WORD = re.compile(r"^[A-Za-z]{2,}[.,:;!?]*$")
        S.TEMPLATES = [(EN[p], g) for p, g in S.TEMPLATES]
    m = MathOCR()
    r = random.Random(a.seed)
    good, times = 0, []
    for _ in range(a.n):
        img, lab = S.make_sample(r)
        res = m(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
        times.append(res["timing_ms"]["total"])
        fb = [x["bbox"] for line in res["lines"] for x in line if x["type"] == "formula"]
        best = max([iou(lab["formulas"][0]["bbox"], b) for b in fb] or [0])
        ok = best > 0.5 and len(fb) == 1
        good += ok
        if a.v or not ok:
            print(f"{'OK ' if ok else 'ERR'} IoU={best:.2f} n={len(fb)} | {res['markdown'].replace(chr(10), ' / ')}"
                  f"  | GT: {lab['formulas'][0]['latex']}")
    print(f"\nТомьёоны байрлал зөв: {good}/{a.n} ({good / a.n:.0%}); "
          f"хугацаа median {np.median(times):.0f}ms, max {max(times)}ms")


if __name__ == "__main__":
    main()
