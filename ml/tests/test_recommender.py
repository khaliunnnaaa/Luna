from ml.common import load_topics
from ml.recommender.recommend import recommend, target_difficulty

TOPICS = load_topics()


def state(mastered=(), grade=10, low=0.3, recommended=()):
    return {"grade": grade, "recommended": list(recommended),
            "mastery": {c: (0.97 if c in mastered else low) for c in TOPICS}}


def test_fresh_student_gets_foundation_topic():
    r = recommend(state())
    assert r["topic"] == "T01"
    assert r["difficulty"] == 1
    assert r["reason"]


def test_prereqs_gate_topics():
    # T01–T03 эзэмшсэн: T04, T06, T10 нээлттэй; T05 (T04 хэрэгтэй) хаалттай
    r = recommend(state(mastered={"T01", "T02", "T03"}))
    assert r["topic"] == "T04"


def test_grade_priority():
    done = {"T01", "T02", "T03", "T04", "T05", "T06"}
    assert recommend(state(mastered=done, grade=10))["topic"] == "T10"
    assert recommend(state(mastered=done, grade=11))["topic"] in {"T07", "T09"}


def test_does_not_repeat_recommended():
    first = recommend(state())
    second = recommend(state(recommended=[first["problem_id"]]))
    assert second["problem_id"] != first["problem_id"]


def test_all_mastered_review():
    s = state(mastered=set(TOPICS))
    s["mastery"]["T08"] = 0.951
    r = recommend(s)
    assert r["topic"] == "T08" and "давтлага" in r["reason"]


def test_target_difficulty():
    assert [target_difficulty(m) for m in (0.1, 0.6, 0.9)] == [1, 2, 3]
