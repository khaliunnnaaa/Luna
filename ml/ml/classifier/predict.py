"""Сургасан ангилагчаар бодлогын сэдэв, хүндийн зэрэг, дэд сэдвийг таамаглана.

Ажиллуулах:  python -m ml.classifier.predict "Тэгшитгэлийг бод. x^2-9=0"
"""
from __future__ import annotations

import sys
from functools import lru_cache

import joblib

from ml.common import MODELS_DIR


@lru_cache(maxsize=1)
def _load():
    paths = {k: MODELS_DIR / f"{k}.joblib" for k in ("topic_clf", "difficulty_clf", "subtopic_knn")}
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Загвар олдсонгүй: {missing}. Эхлээд: python -m ml.classifier.train")
    return {k: joblib.load(p) for k, p in paths.items()}


def predict(text: str) -> dict:
    """{"topic", "difficulty", "confidence", "topic_proba"} буцаана."""
    m = _load()
    topic_model = m["topic_clf"]["model"]
    proba = topic_model.predict_proba([text])[0]
    best = int(proba.argmax())
    difficulty = int(m["difficulty_clf"]["model"].predict([text])[0])
    return {
        "topic": str(topic_model.classes_[best]),
        "difficulty": difficulty,
        "confidence": round(float(proba[best]), 3),
        "topic_proba": {str(c): round(float(p), 3) for c, p in zip(topic_model.classes_, proba)},
    }


def suggest_subtopics(text: str, topic: str | None = None, k: int = 3) -> list[str]:
    """Хамгийн ойрын бодлогуудын дэд сэдвийг (давхардалгүй) санал болгоно.
    `topic` өгвөл зөвхөн тухайн сэдвийн бодлогуудаас хайна."""
    idx = _load()["subtopic_knn"]
    q = idx["features"].transform([text])
    _, nbr = idx["nn"].kneighbors(q, n_neighbors=len(idx["subtopics"]))
    out: list[str] = []
    for j in nbr[0]:
        if topic and idx["topics"][j] != topic:
            continue
        if idx["subtopics"][j] not in out:
            out.append(idx["subtopics"][j])
        if len(out) == k:
            break
    return out


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "Тэгшитгэлийг бод. x^2-9=0"
    r = predict(query)
    print(query, "->", {k: v for k, v in r.items() if k != "topic_proba"})
    print("Дэд сэдэв:", suggest_subtopics(query, r["topic"]))
