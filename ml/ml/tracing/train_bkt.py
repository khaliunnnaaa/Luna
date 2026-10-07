"""Мэдлэг хянах загвар (FR-08): ASSISTments 2009 дээр pyBKT-ээр BKT сургана.

- Train/test-ийг сурагчаар (user_id) 80/20 хуваана — нэг сурагчийн хариулт хоёр талд
  зэрэг орохгүй (data leakage-ээс сэргийлнэ).
- Зорилт: тест дээрх AUC ≥ 0.70.
- Сурсан параметрийн (prior, learn, guess, slip) медианыг T01–T10 сэдэв бүрийн анхны
  параметр болгож config/bkt_params.yaml-д хадгална.

Ажиллуулах:  python -m ml.tracing.train_bkt  [--max-skills N]
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import date

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from ml.common import CONFIG_DIR, RAW_DIR, REPORTS_DIR, SEED, load_topics
from ml.report import update_section

DATA_PATH = RAW_DIR / "assistments_2009" / "as_pybkt.csv"
AUC_TARGET = 0.70
PARAM_KEYS = {"prior": "prior", "learns": "learn", "guesses": "guess", "slips": "slip"}


def load_assistments(max_skills: int | None = None) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(DATA_PATH, encoding="latin1", low_memory=False,
                      usecols=["order_id", "user_id", "skill_name", "correct"])
    stats = {"rows_raw": len(raw), "rows_no_skill": int(raw["skill_name"].isna().sum())}
    df = raw.dropna(subset=["skill_name"])
    # pyBKT хувилбарт ижил (order_id, skill) мөр олон удаа давтагдсан байдаг тул хасна
    before = len(df)
    df = df.drop_duplicates(subset=["order_id", "skill_name"])
    stats["rows_duplicate"] = before - len(df)
    if max_skills:
        top = df["skill_name"].value_counts().index[:max_skills]
        df = df[df["skill_name"].isin(top)]
    df = df.sort_values(["user_id", "order_id"]).reset_index(drop=True)
    stats.update(rows=len(df), students=int(df["user_id"].nunique()), skills=int(df["skill_name"].nunique()),
                 correct_rate=float(df["correct"].mean()))
    return df, stats


def main():
    from pyBKT.models import Model  # импорт удаан тул энд

    ap = argparse.ArgumentParser()
    ap.add_argument("--max-skills", type=int, default=None, help="хурдан туршихад хамгийн их өгөгдөлтэй N skill")
    args = ap.parse_args()

    df, stats = load_assistments(args.max_skills)
    print(f"ASSISTments: {stats}")

    split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    tr_idx, te_idx = next(split.split(df, groups=df["user_id"]))
    train, test = df.iloc[tr_idx], df.iloc[te_idx]
    assert not set(train["user_id"]) & set(test["user_id"]), "сурагч давхацсан!"
    test = test[test["skill_name"].isin(set(train["skill_name"]))]
    print(f"train: {len(train)} мөр / {train.user_id.nunique()} сурагч,  "
          f"test: {len(test)} мөр / {test.user_id.nunique()} сурагч")

    t0 = time.time()
    model = Model(seed=SEED, num_fits=1, parallel=False)  # macOS spawn дээр pool гацдаг
    model.fit(data=train)
    fit_sec = time.time() - t0
    auc = float(model.evaluate(data=test, metric="auc"))
    rmse = float(model.evaluate(data=test, metric="rmse"))

    # Харьцуулах энгийн baseline: skill бүрийн train дээрх зөв хариултын хувь
    rate = train.groupby("skill_name")["correct"].mean()
    baseline_auc = float(roc_auc_score(test["correct"], test["skill_name"].map(rate)))
    print(f"BKT AUC {auc:.4f}  RMSE {rmse:.4f}  (baseline AUC {baseline_auc:.4f}),  сургалт {fit_sec:.0f} сек")

    params = model.params().reset_index()
    per_skill = params[params["param"].isin(PARAM_KEYS)].pivot_table(
        index="skill", columns="param", values="value", aggfunc="first")
    median = {PARAM_KEYS[k]: round(float(per_skill[k].median()), 4) for k in PARAM_KEYS}
    quart = {PARAM_KEYS[k]: [round(float(per_skill[k].quantile(q)), 4) for q in (0.25, 0.75)] for k in PARAM_KEYS}
    print(f"Медиан параметр: {median}")

    topics = load_topics()
    cfg = {
        "source": "ASSISTments 2009 (pyBKT as.csv), pyBKT Model(seed=42, num_fits=1, parallel=False)",
        "trained_on": str(date.today()),
        "n_skills": int(len(per_skill)),
        "test_auc": round(auc, 4),
        "note": ("Манай системд хэрэглэгчийн өгөгдөл одоогоор байхгүй тул ASSISTments-ийн бүх skill-ийн "
                 "параметрийн медианыг сэдэв бүрт анхны утга болгосон. Хэрэглэгчийн өгөгдөл хуримтлагдсаны "
                 "дараа сэдэв тус бүрээр дахин сургана."),
        "default": median,
        "topics": {code: dict(median) for code in topics},
    }
    with open(CONFIG_DIR / "bkt_params.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)

    metrics = {"data": stats, "train_rows": len(train), "test_rows": len(test),
               "train_students": int(train.user_id.nunique()), "test_students": int(test.user_id.nunique()),
               "auc": auc, "rmse": rmse, "baseline_skill_rate_auc": baseline_auc, "fit_seconds": fit_sec,
               "median_params": median, "iqr_params": quart, "max_skills": args.max_skills}
    REPORTS_DIR.mkdir(exist_ok=True)
    with open(REPORTS_DIR / "bkt_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    if not args.max_skills:  # зөвхөн бүрэн сургалтын үр дүнг тайланд бичнэ
        update_section("tracing", render_markdown(metrics))


def render_markdown(m: dict) -> str:
    d = m["data"]
    ok = "✅ хүрсэн" if m["auc"] >= AUC_TARGET else "❌ хүрээгүй"
    rows = "\n".join(f"| {k} | {v} | {m['iqr_params'][k][0]} – {m['iqr_params'][k][1]} |"
                     for k, v in m["median_params"].items())
    return f"""## 2. Мэдлэг хянах загвар — BKT (FR-08)

Өгөгдөл: ASSISTments 2009 (pyBKT хувилбар). Түүхий {d['rows_raw']:,} мөрөөс skill-гүй {d['rows_no_skill']:,},
давхардсан (order_id, skill) {d['rows_duplicate']:,} мөрийг хассан → {d['rows']:,} мөр, {d['students']:,} сурагч, {d['skills']} skill.
Сурагчаар (user_id) 80/20 хуваасан: train {m['train_rows']:,} мөр / {m['train_students']:,} сурагч,
test {m['test_rows']:,} мөр / {m['test_students']:,} сурагч. Сурагч давхцаагүйг кодонд assert-аар шалгадаг.

| Метрик | Утга |
|---|---|
| **AUC (test)** | **{m['auc']:.4f}** (зорилт ≥ {AUC_TARGET} — {ok}) |
| RMSE (test) | {m['rmse']:.4f} |
| Baseline AUC (skill-ийн дундаж зөв хувь) | {m['baseline_skill_rate_auc']:.4f} |
| Сургалтын хугацаа | {m['fit_seconds']:.0f} сек (CPU) |

`config/bkt_params.yaml`-д хадгалсан анхны параметр (skill-үүдийн медиан, IQR):

| Параметр | Медиан | IQR (25–75%) |
|---|---|---|
{rows}

**Яагаад медиан вэ:** манай системд хэрэглэгчийн хариултын түүх хараахан байхгүй тул T01–T10 сэдэв бүрт
тусгайлан параметр сургах боломжгүй. ASSISTments-ийн математикийн skill-үүдийн медиан нь
"ердийн математикийн ур чадвар" ямар хурдаар эзэмшигддэг тухай бодит өгөгдөлд суурилсан, хэт утгад
(outlier) тэсвэртэй анхны таамаг болно. Систем ашиглагдаж эхэлсний дараа сэдэв тус бүрээр дахин сургана.
"""


if __name__ == "__main__":
    main()
