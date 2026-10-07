"""Урьдач холбоосын граф: циклгүй, бүх холбоос зөв."""
import pandas as pd
import pytest

from ml.common import BANK_PATH, Topic, load_topics
from ml.recommender.recommend import topological_order


def test_config_graph_is_acyclic():
    topics = load_topics()
    order = topological_order(topics)
    assert sorted(order) == sorted(topics)
    pos = {c: i for i, c in enumerate(order)}
    for t in topics.values():
        for p in t.prereq:
            assert pos[p] < pos[t.code], f"{p} нь {t.code}-ээс өмнө байх ёстой"


def test_cycle_is_detected():
    topics = {"A": Topic("A", "a", 10, ["C"]), "B": Topic("B", "b", 10, ["A"]), "C": Topic("C", "c", 10, ["B"])}
    with pytest.raises(ValueError, match="цикл"):
        topological_order(topics)


def test_unknown_prereq_is_detected():
    with pytest.raises(ValueError, match="олдсонгүй"):
        topological_order({"A": Topic("A", "a", 10, ["Z"])})


def test_config_matches_bank_graph():
    """config/topics.csv нь бодлогын_сан.xlsx-ийн "Сэдвийн_граф" хуудастай ижил ирмэгтэй."""
    edges_xlsx = pd.read_excel(BANK_PATH, sheet_name="Сэдвийн_граф")
    xlsx = set(zip(edges_xlsx.iloc[:, 0], edges_xlsx.iloc[:, 1]))
    config = {(p, t.code) for t in load_topics().values() for p in t.prereq}
    assert config == xlsx
