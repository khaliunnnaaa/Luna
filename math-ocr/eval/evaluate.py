"""OCR үнэлгээ — NFR-05 (томьёо зөв танилт ≥ 85%) ба NFR-02 (≤ 5 сек).

Өгөгдлийн формат (өөрсдийн авсан ≥300 зураг):
    data/real/images/*.jpg
    data/real/labels.jsonl   мөр бүр:
        {"image": "images/001.jpg",
         "markdown": "Тэгшитгэлийг бод: $x^2-5x+6=0$"}
    (markdown дахь $...$ = томьёо, бусад нь текст. Нэг зурагт хэд хэдэн томьёо байж болно.)

Ажиллуулах:
    python -m eval.evaluate --data data/real                 # бүтэн pipeline
    python -m eval.evaluate --data data/real --split test    # labels_test.jsonl
    python -m eval.evaluate --crops data/synth               # зөвхөн томьёо таних загвар (crops + pix2tex_math.txt)

Хэмжүүр:
    formula_exact      — хэвшүүлсэн LaTeX яг таарсан томьёоны хувь  (NFR-05 гол үзүүлэлт)
    formula_token_sim  — 1 - token edit distance / урт (хэсэгчлэн зөвийг харуулна)
    text_cer           — монгол текстийн тэмдэгтийн алдааны хувь (бага нь сайн)
    latency p50/p95    — NFR-02
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time

import numpy as np

from ocr.latex_utils import edit_distance, normalize_for_match, tokenize

RE_MATH = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$", re.S)


def split_markdown(md: str) -> tuple[str, list[str]]:
    formulas = [a or b for a, b in RE_MATH.findall(md)]
    text = RE_MATH.sub(" ", md)
    return re.sub(r"\s+", " ", text).strip(), formulas


def token_sim(a: str, b: str) -> float:
    ta, tb = tokenize(normalize_for_match(a)), tokenize(normalize_for_match(b))
    if not ta and not tb:
        return 1.0
    return 1 - edit_distance(ta, tb) / max(len(ta), len(tb))


def cer(pred: str, gt: str) -> float:
    if not gt:
        return 0.0 if not pred else 1.0
    return edit_distance(list(pred), list(gt)) / len(gt)


def match_formulas(pred: list[str], gt: list[str]) -> list[tuple[str, str | None, float]]:
    """GT томьёо бүрт хамгийн төстэй (давхардуулахгүй) таамаглалыг оноох."""
    used, out = set(), []
    for g in gt:
        best, bi = 0.0, None
        for i, p in enumerate(pred):
            if i in used:
                continue
            s = token_sim(p, g)
            if s > best:
                best, bi = s, i
        if bi is not None:
            used.add(bi)
        out.append((g, pred[bi] if bi is not None else None, best))
    return out


def eval_pipeline(data: str, labels: str, limit: int | None, out_csv: str) -> dict:
    from ocr import MathOCR
    ocr = MathOCR()
    rows, lat, exact, sims, cers, n_review = [], [], [], [], [], 0
    with open(os.path.join(data, labels), encoding="utf-8") as f:
        items = [json.loads(l) for l in f if l.strip()]
    if limit:
        items = items[:limit]
    for it in items:
        gt_text, gt_f = split_markdown(it["markdown"])
        t0 = time.perf_counter()
        res = ocr(os.path.join(data, it["image"]))
        lat.append(time.perf_counter() - t0)
        n_review += res["needs_review"]
        pr_text, pr_f = split_markdown(res["markdown"])
        for g, p, s in match_formulas(pr_f, gt_f):
            ok = p is not None and normalize_for_match(p) == normalize_for_match(g)
            exact.append(ok)
            sims.append(s)
            rows.append({"image": it["image"], "gt": g, "pred": p or "", "exact": int(ok), "token_sim": round(s, 3)})
        cers.append(cer(pr_text, gt_text))
    _write_csv(out_csv, rows)
    return _summary(exact, sims, lat, cers, len(items), n_review)


def eval_crops(data: str, limit: int | None, out_csv: str) -> dict:
    """Томьёо таних загварыг (pix2tex) layout-аас тусад нь үнэлнэ."""
    import cv2
    from ocr.formula_ocr import FormulaRecognizer
    rec = FormulaRecognizer()
    if not rec.available:
        raise SystemExit("pix2tex суулгаагүй байна: pip install 'pix2tex[api]'")
    gts = open(os.path.join(data, "pix2tex_math.txt"), encoding="utf-8").read().splitlines()
    if limit:
        gts = gts[:limit]
    rows, exact, sims, lat = [], [], [], []
    for i, g in enumerate(gts):
        img = cv2.imread(os.path.join(data, "crops", f"{i:07d}.png"), cv2.IMREAD_GRAYSCALE)
        t0 = time.perf_counter()
        p = rec.recognize(img)["latex"]
        lat.append(time.perf_counter() - t0)
        ok = normalize_for_match(p) == normalize_for_match(g)
        s = token_sim(p, g)
        exact.append(ok)
        sims.append(s)
        rows.append({"image": f"{i:07d}.png", "gt": g, "pred": p, "exact": int(ok), "token_sim": round(s, 3)})
    _write_csv(out_csv, rows)
    return _summary(exact, sims, lat, [], len(gts), 0)


def _write_csv(path: str, rows: list[dict]) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # Excel-д кирилл зөв харагдана
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def _summary(exact, sims, lat, cers, n_img, n_review) -> dict:
    lat_ms = np.array(lat) * 1000
    fe = float(np.mean(exact)) if exact else 0.0
    return {
        "images": n_img,
        "formulas": len(exact),
        "formula_exact": round(fe, 4),
        "formula_token_sim": round(float(np.mean(sims)), 4) if sims else 0.0,
        "text_cer": round(float(np.mean(cers)), 4) if cers else None,
        "needs_review_rate": round(n_review / n_img, 3) if n_img else 0,
        "latency_ms_p50": round(float(np.percentile(lat_ms, 50))) if len(lat_ms) else None,
        "latency_ms_p95": round(float(np.percentile(lat_ms, 95))) if len(lat_ms) else None,
        "NFR-05 (>=85%)": "PASS" if fe >= 0.85 else "FAIL",
        "NFR-02 (p95<=5s)": "PASS" if len(lat_ms) and np.percentile(lat_ms, 95) <= 5000 else "FAIL",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="labels.jsonl бүхий хавтас (бүтэн pipeline)")
    ap.add_argument("--split", default=None, help="test -> labels_test.jsonl")
    ap.add_argument("--crops", help="crops/ + pix2tex_math.txt бүхий хавтас (зөвхөн томьёо)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default="eval_report")
    a = ap.parse_args()
    if a.crops:
        rep = eval_crops(a.crops, a.limit, a.out + "_crops.csv")
    elif a.data:
        labels = f"labels_{a.split}.jsonl" if a.split else "labels.jsonl"
        rep = eval_pipeline(a.data, labels, a.limit, a.out + ".csv")
    else:
        ap.error("--data эсвэл --crops заана уу")
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    with open(a.out + ".json", "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
