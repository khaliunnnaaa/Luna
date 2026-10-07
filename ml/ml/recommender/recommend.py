"""Дараагийн бодлого санал болгогч (FR-09/11) — дүрэмд суурилсан эхний хувилбар.

Логик:
  1. Урьдач сэдвүүд нь бүгд эзэмшигдсэн (mastery ≥ 0.95) боловч өөрөө эзэмшигдээгүй сэдвүүд
     нь "нээлттэй" сэдэв болно.
  2. Нээлттэй сэдвүүдээс сурагчийн ангид (grade) хамаарахыг нь түрүүлж, дараа нь урьдач
     графын дарааллаар (топологийн эрэмбэ) сонгоно.
  3. Тухайн сэдвийн mastery-д тохирох хүндийн зэргийн, өмнө санал болгоогүй бодлогыг сонгоно.
  4. Бүх сэдэв эзэмшигдсэн бол хамгийн бага mastery-тэй сэдвээр давтлага санал болгоно.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from ml.common import COL_DIFFICULTY, COL_ID, COL_TOPIC, MASTERY_THRESHOLD, Topic, load_bank, load_topics


def topological_order(topics: dict[str, Topic]) -> list[str]:
    """Kahn-ийн алгоритм. Граф цикл агуулсан эсвэл байхгүй сэдэв заасан бол ValueError."""
    for t in topics.values():
        unknown = [p for p in t.prereq if p not in topics]
        if unknown:
            raise ValueError(f"{t.code}-ийн урьдач сэдэв олдсонгүй: {unknown}")
    indegree = {c: len(t.prereq) for c, t in topics.items()}
    children: dict[str, list[str]] = {c: [] for c in topics}
    for c, t in topics.items():
        for p in t.prereq:
            children[p].append(c)
    queue = sorted(c for c, d in indegree.items() if d == 0)
    order: list[str] = []
    while queue:
        c = queue.pop(0)
        order.append(c)
        for ch in sorted(children[c]):
            indegree[ch] -= 1
            if indegree[ch] == 0:
                queue.append(ch)
        queue.sort()
    if len(order) != len(topics):
        cyclic = sorted(set(topics) - set(order))
        raise ValueError(f"Урьдач холбоосын граф цикл агуулж байна: {cyclic}")
    return order


def target_difficulty(mastery: float) -> int:
    """Mastery-г бодлогын сангийн 1–3 түвшинд буулгана."""
    if mastery < 0.5:
        return 1
    if mastery < 0.8:
        return 2
    return 3


@lru_cache(maxsize=1)
def _bank() -> pd.DataFrame:
    return load_bank()[[COL_ID, COL_TOPIC, COL_DIFFICULTY]]


def pick_problem(bank: pd.DataFrame, topic: str, difficulty: int, exclude: list[str]) -> pd.Series | None:
    """Сэдвээс хүссэн түвшинд хамгийн ойр, өмнө санал болгоогүй бодлого.
    Бүгдийг санал болгосон бол хамгийн эрт санал болгосныг нь давтана."""
    pool = bank[bank[COL_TOPIC] == topic].copy()
    if pool.empty:
        return None
    pool["dist"] = (pool[COL_DIFFICULTY] - difficulty).abs()
    fresh = pool[~pool[COL_ID].isin(exclude)]
    if not fresh.empty:
        return fresh.sort_values(["dist", COL_ID]).iloc[0]
    last_seen = {pid: i for i, pid in enumerate(exclude)}
    pool["seen"] = pool[COL_ID].map(last_seen)
    return pool.sort_values(["dist", "seen"]).iloc[0]


def recommend(state: dict, topics: dict[str, Topic] | None = None, bank: pd.DataFrame | None = None) -> dict:
    topics = topics or load_topics()
    bank = _bank() if bank is None else bank
    order = topological_order(topics)
    mastery: dict[str, float] = state["mastery"]
    grade = int(state.get("grade", 10))
    mastered = {c: mastery.get(c, 0.0) >= MASTERY_THRESHOLD for c in topics}

    open_topics = [c for c in order if not mastered[c] and all(mastered[p] for p in topics[c].prereq)]
    if open_topics:
        open_topics.sort(key=lambda c: (topics[c].grade != grade, order.index(c)))
        topic = open_topics[0]
        prereq = topics[topic].prereq
        reason = (f"{topic} ({topics[topic].name}): эзэмшил {mastery[topic]:.2f} < {MASTERY_THRESHOLD}. "
                  + (f"Урьдач сэдэв {', '.join(prereq)} бүгд эзэмшигдсэн. " if prereq else "Урьдач сэдэвгүй суурь сэдэв. ")
                  + ("Таны ангийн сэдэв." if topics[topic].grade == grade
                     else f"{grade}-р ангийн нээлттэй сэдэв алга тул {topics[topic].grade}-р ангийнхыг санал болгов."))
    else:
        topic = min(topics, key=lambda c: (mastery.get(c, 0.0), c))
        reason = f"Бүх сэдэв эзэмшигдсэн. Хамгийн бага эзэмшилтэй {topic} ({mastery[topic]:.2f})-ээр давтлага."

    level = target_difficulty(mastery[topic])
    row = pick_problem(bank, topic, level, state.get("recommended", []))
    if row is None:
        return {"problem_id": None, "topic": topic, "difficulty": None,
                "reason": reason + " Энэ сэдэвт бодлого алга."}
    diff = int(row[COL_DIFFICULTY])
    reason += f" Эзэмшилд тохирох түвшин {level}" + ("." if diff == level else f", хамгийн ойр нь {diff}.")
    return {"problem_id": str(row[COL_ID]), "topic": topic, "difficulty": diff, "reason": reason}
