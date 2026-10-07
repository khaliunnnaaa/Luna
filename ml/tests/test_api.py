import pytest

from conftest import needs_models
from ml import api
from ml.tracing.mastery import JSONStudentStore


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "_store", JSONStudentStore(tmp_path))


@needs_models
def test_classify_problem_shape():
    r = api.classify_problem("Тэнцэтгэл бишийг бод. 2x-3>5")
    assert set(r) == {"topic", "difficulty", "confidence"}


def test_update_and_recommend_flow():
    api.register_student("demo", grade=10)
    m = api.update_mastery("demo", "T01", True)
    assert set(m) == {f"T{i:02d}" for i in range(1, 11)}
    r1 = api.recommend_next("demo")
    r2 = api.recommend_next("demo")
    assert set(r1) == {"problem_id", "topic", "difficulty", "reason"}
    assert r1["problem_id"] != r2["problem_id"]
