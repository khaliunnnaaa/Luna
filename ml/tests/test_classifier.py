import numpy as np

from conftest import needs_models
from ml.classifier.features import FEATURE_NAMES, latex_features
from ml.common import COL_DIFFICULTY, COL_TOPIC, load_bank


def test_bank_loads_without_empty_rows():
    bank = load_bank()
    assert len(bank) == 200  # 2026-10-09: сэдэв бүрт 20
    assert bank["input"].str.len().min() > 0
    assert set(bank[COL_DIFFICULTY]) == {1, 2, 3}
    assert bank[COL_TOPIC].value_counts().eq(20).all()


def test_latex_features_language_independent():
    mn = latex_features("Тэгшитгэлийг бод. \\log_2 x = 3")
    en = latex_features("Solve the equation. \\log_2 x = 3")
    assert len(mn) == len(FEATURE_NAMES)
    i = FEATURE_NAMES.index("log")
    assert mn[i] > 0 and mn[i] == en[i]


def test_unicode_and_latex_counted_same():
    a = latex_features("√x ≤ 2")
    b = latex_features("\\sqrt{x} \\le 2")
    for name in ("sqrt", "inequality"):
        i = FEATURE_NAMES.index(name)
        assert a[i] == b[i] > 0


@needs_models
def test_predict_schema():
    from ml.classifier.predict import predict, suggest_subtopics
    r = predict("Тэгшитгэлийг бод. x^2-9=0")
    assert r["topic"] in {f"T{i:02d}" for i in range(1, 11)}
    assert r["difficulty"] in {1, 2, 3}
    assert 0 <= r["confidence"] <= 1
    assert np.isclose(sum(r["topic_proba"].values()), 1, atol=0.01)
    assert len(suggest_subtopics("\\sin 30^\\circ", "T09")) == 3
