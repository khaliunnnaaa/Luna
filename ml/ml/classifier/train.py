"""Бодлого ангилагч (FR-04): сэдэв (T01–T10) ба хүндийн зэрэг (1–3).

Хувилбарууд:
  A  — TF-IDF (тэмдэгтийн 2–5 n-gram) + LogisticRegression
  B  — A + LaTeX/математикийн тэмдэгтийн шинж (хэлнээс хамаарахгүй)
  C  — B + MATH (Hendrycks)-ийн сул шошготой бодлогоор сургалтыг нэмэгдүүлсэн (зөвхөн сэдэвт)

Үнэлгээ: RepeatedStratifiedKFold (3 fold × 10 давталт), macro-F1 дундаж ± стандарт хазайлт.
Тест fold үргэлж зөвхөн бодлогын_сан.xlsx-ийн бодлого байна.

Ажиллуулах:  python -m ml.classifier.train
"""
from __future__ import annotations

import json
import re

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402
from sklearn.dummy import DummyClassifier  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import confusion_matrix, f1_score  # noqa: E402
from sklearn.model_selection import RepeatedStratifiedKFold  # noqa: E402
from sklearn.neighbors import NearestNeighbors  # noqa: E402
from sklearn.pipeline import FeatureUnion, Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from ml.classifier.features import LatexFeatures  # noqa: E402
from ml.common import (  # noqa: E402
    COL_DIFFICULTY, COL_ID, COL_SUBTOPIC, COL_TEXT, COL_TOPIC, CONFIG_DIR, MODELS_DIR, RAW_DIR,
    REPORTS_DIR, SEED, load_bank,
)
from ml.report import update_section  # noqa: E402

N_SPLITS, N_REPEATS = 3, 10
MATH_WEIGHT = 0.1  # MATH-ийн бодлого бүрийн жин (урьдчилан тогтоосон, тохируулаагүй)


def build_pipeline(variant: str) -> Pipeline:
    tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, lowercase=True)
    if variant == "A":
        features = tfidf
    else:  # B, C
        latex = Pipeline([("latex", LatexFeatures()), ("scale", StandardScaler())])
        features = FeatureUnion([("tfidf", tfidf), ("latex", latex)])
    clf = LogisticRegression(C=10.0, max_iter=5000, random_state=SEED)
    return Pipeline([("features", features), ("clf", clf)])


# ---------------------------------------------------------------- MATH сул шошго
def load_math_weak(mapping_path=CONFIG_DIR / "topic_mapping.yaml") -> pd.DataFrame:
    """MATH-ийн бодлогуудад topic_mapping.yaml-ийн дүрмээр T-код онооно."""
    cfg = yaml.safe_load(open(mapping_path, encoding="utf-8"))
    rows = []
    for subject, rules in cfg["subjects"].items():
        for path in sorted((RAW_DIR / "math_hendrycks").glob(f"{subject}_*.jsonl")):
            for line in open(path, encoding="utf-8"):
                problem = json.loads(line)["problem"]
                for rule in rules:
                    if "exclude" in rule:
                        if re.search(rule["exclude"], problem, flags=re.I):
                            break
                        continue
                    if re.search(rule["pattern"], problem, flags=re.I):
                        rows.append({"input": problem, "topic": rule["topic"], "subject": subject})
                        break
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    cap = cfg.get("max_per_topic", 300)
    parts = [g.sample(min(len(g), cap), random_state=SEED) for _, g in df.groupby("topic")]
    return pd.concat(parts).reset_index(drop=True)


# ---------------------------------------------------------------- үнэлгээ
def cross_validate(X, y, variant: str, extra: pd.DataFrame | None = None):
    """Давтагдсан stratified k-fold. Fold бүрийн macro-F1 ба нийт OOF таамаглалыг буцаана."""
    cv = RepeatedStratifiedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=SEED)
    scores, y_true, y_pred = [], [], []
    for train_idx, test_idx in cv.split(X, y):
        X_tr, y_tr = list(X[train_idx]), list(y[train_idx])
        weights = [1.0] * len(X_tr)
        if extra is not None and not extra.empty:
            X_tr += list(extra["input"])
            y_tr += list(extra["topic"])
            weights += [MATH_WEIGHT] * len(extra)
        if variant == "dummy":
            model = DummyClassifier(strategy="stratified", random_state=SEED)
            model.fit(X_tr, y_tr)
        else:
            model = build_pipeline(variant)
            model.fit(X_tr, y_tr, clf__sample_weight=np.asarray(weights))
        pred = model.predict(list(X[test_idx]))
        scores.append(f1_score(y[test_idx], pred, average="macro"))
        y_true += list(y[test_idx])
        y_pred += list(pred)
    return np.asarray(scores), y_true, y_pred


def plot_confusion(y_true, y_pred, labels, title, path):
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_norm = cm / cm.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(1 + 0.6 * len(labels), 0.8 + 0.55 * len(labels)))
    ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=45)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Таамагласан")
    ax.set_ylabel("Жинхэнэ")
    ax.set_title(title, fontsize=10)
    for i in range(len(labels)):
        for j in range(len(labels)):
            if cm[i, j]:
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=8,
                        color="white" if cm_norm[i, j] > 0.5 else "black")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return cm


# ---------------------------------------------------------------- дэд сэдэв (kNN)
def build_subtopic_index(bank: pd.DataFrame):
    vec = build_pipeline("B").named_steps["features"]
    matrix = vec.fit_transform(list(bank["input"]))
    nn = NearestNeighbors(metric="cosine").fit(matrix)
    return {"features": vec, "nn": nn, "subtopics": list(bank[COL_SUBTOPIC]),
            "topics": list(bank[COL_TOPIC]), "ids": list(bank[COL_ID])}


def eval_subtopic_loo(bank: pd.DataFrame, k: int = 3) -> dict:
    """Leave-one-out: хамгийн ойрын k хөршийн дэд сэдэвт жинхэнэ дэд сэдэв орсон эсэх.
    Сангийн ганц удаа гарсан дэд сэдвийг таах боломжгүй тул зөвхөн ≥2 удаа гарсныг тооцно."""
    counts = bank[COL_SUBTOPIC].value_counts()
    eligible = bank.index[bank[COL_SUBTOPIC].map(counts) >= 2]
    hits1 = hitsk = 0
    for i in eligible:
        rest = bank.drop(index=i)
        idx = build_subtopic_index(rest)
        q = idx["features"].transform([bank.at[i, "input"]])
        _, nbr = idx["nn"].kneighbors(q, n_neighbors=len(rest))
        subs = []
        for j in nbr[0]:
            s = idx["subtopics"][j]
            if s not in subs:
                subs.append(s)
            if len(subs) == k:
                break
        hits1 += subs[0] == bank.at[i, COL_SUBTOPIC]
        hitsk += bank.at[i, COL_SUBTOPIC] in subs
    n = len(eligible)
    return {"n_eval": int(n), "top1": hits1 / n, f"top{k}": hitsk / n}


# ---------------------------------------------------------------- үндсэн
def main():
    REPORTS_DIR.mkdir(exist_ok=True)
    MODELS_DIR.mkdir(exist_ok=True)
    bank = load_bank()
    X = bank["input"].to_numpy()
    y_topic = bank[COL_TOPIC].to_numpy()
    y_diff = bank[COL_DIFFICULTY].to_numpy()
    topics = sorted(set(y_topic))
    print(f"Бодлогын сан: {len(bank)} бодлого, {len(topics)} сэдэв")

    math_weak = load_math_weak()
    math_dist = math_weak["topic"].value_counts().sort_index().to_dict() if not math_weak.empty else {}
    print(f"MATH сул шошго: {len(math_weak)} бодлого {math_dist}")

    results = {"topic": {}, "difficulty": {}}
    preds = {}
    for variant in ["dummy", "A", "B", "C"]:
        extra = math_weak if variant == "C" else None
        v = "B" if variant == "C" else variant
        s, yt, yp = cross_validate(X, y_topic, v, extra)
        results["topic"][variant] = {"macro_f1_mean": s.mean(), "macro_f1_std": s.std(),
                                     "min": s.min(), "max": s.max()}
        preds[variant] = (yt, yp)
        print(f"  сэдэв  {variant:5s}: macro-F1 {s.mean():.3f} ± {s.std():.3f}")
    diff_preds = {}
    for variant in ["dummy", "A", "B"]:
        s, yt, yp = cross_validate(X, y_diff, variant)
        results["difficulty"][variant] = {"macro_f1_mean": s.mean(), "macro_f1_std": s.std(),
                                          "min": s.min(), "max": s.max()}
        diff_preds[variant] = (yt, yp)
        print(f"  түвшин {variant:5s}: macro-F1 {s.mean():.3f} ± {s.std():.3f}")

    # Хамгийн өндөр дундаж macro-F1-тэй хувилбарыг сонгоно (dummy-г оролцуулахгүй)
    best_topic = max("ABC", key=lambda v: results["topic"][v]["macro_f1_mean"])
    best_diff = max("AB", key=lambda v: results["difficulty"][v]["macro_f1_mean"])

    cm_topic = plot_confusion(*preds[best_topic], topics,
                              f"Сэдэв — хувилбар {best_topic} ({N_REPEATS}×{N_SPLITS}-fold OOF нийлбэр)",
                              REPORTS_DIR / "confusion_topic.png")
    cm_diff = plot_confusion(*diff_preds[best_diff], [1, 2, 3],
                             f"Түвшин — хувилбар {best_diff}", REPORTS_DIR / "confusion_difficulty.png")
    # Хувилбар A-ийн confusion-ийг харьцуулалтад бас хадгална
    plot_confusion(*preds["A"], topics, "Сэдэв — хувилбар A", REPORTS_DIR / "confusion_topic_A.png")

    sub_eval = eval_subtopic_loo(bank)
    print(f"  дэд сэдэв kNN (LOO): {sub_eval}")

    # Эцсийн загварыг бүх өгөгдөл дээр сургана
    def fit_final(variant, y, extra=None):
        model = build_pipeline("B" if variant == "C" else variant)
        Xf, yf, w = list(X), list(y), [1.0] * len(X)
        if extra is not None:
            Xf += list(extra["input"]); yf += list(extra["topic"]); w += [MATH_WEIGHT] * len(extra)
        return model.fit(Xf, yf, clf__sample_weight=np.asarray(w))

    topic_model = fit_final(best_topic, y_topic, math_weak if best_topic == "C" else None)
    diff_model = fit_final(best_diff, y_diff)
    joblib.dump({"model": topic_model, "variant": best_topic}, MODELS_DIR / "topic_clf.joblib")
    joblib.dump({"model": diff_model, "variant": best_diff}, MODELS_DIR / "difficulty_clf.joblib")
    joblib.dump(build_subtopic_index(bank), MODELS_DIR / "subtopic_knn.joblib")

    text_counts = bank[COL_TEXT].value_counts()
    n_shared_text = int(bank[COL_TEXT].map(text_counts).gt(1).sum())
    metrics = {"n_problems": len(bank), "n_shared_text": n_shared_text, "cv": f"RepeatedStratifiedKFold({N_SPLITS}x{N_REPEATS}, seed={SEED})",
               "math_weak_labels": math_dist, "math_weight": MATH_WEIGHT,
               "best_topic_variant": best_topic, "best_difficulty_variant": best_diff,
               "results": results, "subtopic_knn_loo": sub_eval,
               "confusion_topic": {"labels": topics, "matrix": cm_topic.tolist()},
               "confusion_difficulty": {"labels": [1, 2, 3], "matrix": cm_diff.tolist()}}
    with open(REPORTS_DIR / "classifier_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=float)
    update_section("classifier", render_markdown(metrics, cm_topic, topics))
    print("Хадгалсан: models/topic_clf.joblib, models/difficulty_clf.joblib, reports/")


def render_markdown(m, cm_topic, topics) -> str:
    names = {"dummy": "Санамсаргүй (stratified dummy)", "A": "A: TF-IDF char 2–5 + LR",
             "B": "B: A + LaTeX шинж", "C": "C: B + MATH сул шошго"}
    lines = ["## 1. Бодлого ангилагч (FR-04)", "",
             f"Өгөгдөл: бодлогын_сан.xlsx, {m['n_problems']} бодлого (сэдэв бүрт 6, түвшин бүрт 2). "
             f"Оролт = `бодлогын_текст` + `томьёо_LaTeX`. Үнэлгээ: {m['cv']}, нийт 30 fold.", "",
             "### Сэдэв (T01–T10)", "", "| Хувилбар | Macro-F1 дундаж | Std | Min | Max |", "|---|---|---|---|---|"]
    for v, r in m["results"]["topic"].items():
        lines.append(f"| {names[v]} | {r['macro_f1_mean']:.3f} | {r['macro_f1_std']:.3f} | {r['min']:.3f} | {r['max']:.3f} |")
    lines += ["", "### Хүндийн зэрэг (1–3)", "", "| Хувилбар | Macro-F1 дундаж | Std | Min | Max |", "|---|---|---|---|---|"]
    for v, r in m["results"]["difficulty"].items():
        lines.append(f"| {names[v]} | {r['macro_f1_mean']:.3f} | {r['macro_f1_std']:.3f} | {r['min']:.3f} | {r['max']:.3f} |")
    # хамгийн их андуурсан хосууд
    off = [(cm_topic[i, j], topics[i], topics[j]) for i in range(len(topics))
           for j in range(len(topics)) if i != j and cm_topic[i, j]]
    off.sort(reverse=True)
    sub = m["subtopic_knn_loo"]
    lines += ["", f"Сонгосон загвар: сэдэв — **{m['best_topic_variant']}**, түвшин — **{m['best_difficulty_variant']}** "
              "(CV-ийн дундаж macro-F1-ээр сонгосон тул сонгогдсон загварын оноо бага зэрэг өөдрөг байж болно).", "",
              f"MATH сул шошго (хувилбар C): {sum(m['math_weak_labels'].values())} бодлого, жин {m['math_weight']} — "
              f"{m['math_weak_labels']}", "",
              "Confusion matrix (10 давталтын out-of-fold таамаглалын нийлбэр, мөр бүр = 60 таамаглал): "
              "`reports/confusion_topic.png`, `reports/confusion_topic_A.png`, `reports/confusion_difficulty.png`.", "",
              "Хамгийн их андуурсан хос (жинхэнэ → таамаг, тоо): "
              + ", ".join(f"{a}→{b} ({c})" for c, a, b in off[:6]), "",
              f"Дэд сэдэв kNN (leave-one-out, ≥2 удаа гарсан {sub['n_eval']} бодлого): "
              f"top-1 {sub['top1']:.3f}, top-3 {sub['top3']:.3f}.", "",
              "**Анхааруулга:** сэдэв бүрт ердөө 6 жишээ, fold бүрийн тест хэсэгт сэдэв бүрээс 2 бодлого л орно. "
              "Иймд fold хоорондын хэлбэлзэл (Min/Max) их, үр дүн тогтворгүй. Мөн "
              f"{m['n_problems']} бодлогын {m['n_shared_text']} нь өөр бодлоготой яг ижил текстэй "
              "(\"Тэгшитгэлийг бод.\", \"Утгыг ол.\" гэх мэт) тул ялгах мэдээлэл ихэвчлэн "
              "LaTeX томьёонд байна. Бодит хэрэглээний гүйцэтгэлийг үнэлэхийн тулд илүү олон, бие даасан "
              "тестийн бодлого хэрэгтэй."]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
