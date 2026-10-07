import pytest

from ml.tracing.mastery import JSONStudentStore, bkt_update, get_state, update_mastery

P = dict(learn=0.1, guess=0.2, slip=0.1)


def test_correct_increases_wrong_decreases():
    assert bkt_update(0.5, True, **P) > 0.5
    assert bkt_update(0.5, False, **P) < 0.5


def test_bkt_formula_value():
    # зөв: post = .5*.9 / (.5*.9 + .5*.2) = .818181...;  p' = post + (1-post)*.1
    post = 0.45 / 0.55
    assert bkt_update(0.5, True, **P) == pytest.approx(post + (1 - post) * 0.1)


def test_stays_in_unit_interval():
    p = 0.5
    for correct in [True] * 30 + [False] * 30:
        p = bkt_update(p, correct, **P)
        assert 0 < p < 1


def test_wrong_answer_still_lowers_after_long_streak():
    p = 0.5
    for _ in range(100):
        p = bkt_update(p, True, **P)
    assert bkt_update(p, False, **P) < p


def test_store_persists(tmp_path):
    store = JSONStudentStore(tmp_path)
    m1 = update_mastery("s1", "T01", True, store=store)
    m2 = update_mastery("s1", "T01", True, store=store)
    assert m2["T01"] > m1["T01"]
    assert len(m1) == 10
    state = get_state("s1", store)
    assert len(state["history"]) == 2


def test_rejects_bad_input(tmp_path):
    store = JSONStudentStore(tmp_path)
    with pytest.raises(ValueError):
        update_mastery("s1", "T99", True, store=store)
    with pytest.raises(ValueError):
        update_mastery("../evil", "T01", True, store=store)
