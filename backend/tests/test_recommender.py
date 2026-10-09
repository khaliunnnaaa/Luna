"""FR-09/11: дараагийн дасгал санал болгогч."""

import pytest
from sqlalchemy import select

from app.services.recommender import target_difficulty, topological_order


def test_topological_order():
    assert topological_order({"c": ["b"], "b": ["a"], "a": []}) == ["a", "b", "c"]
    # цикл: алдаа өгөхгүй, үлдсэнийг ард нь залгана
    assert set(topological_order({"a": ["b"], "b": ["a"]})) == {"a", "b"}


def test_target_difficulty():
    assert [target_difficulty(x) for x in (0.1, 0.5, 0.79, 0.8, 0.99)] == [1, 2, 2, 3, 3]


def _problem(topic, difficulty, answer, code):
    return {
        "code": code,
        "topic_id": topic,
        "difficulty": difficulty,
        "statement": f"{code}: $x$",
        "answers": [answer],
        "hints": ["h1"],
    }


@pytest.fixture()
def bank(client, admin_headers):
    """T01 (суурь) ← T02. T01-д 3 түвшний 3 бодлого, T02-т 1 бодлого."""
    for t in (
        {"id": "T01", "name": "Суурь", "grade": 10},
        {"id": "T02", "name": "Дараагийн", "grade": 10, "prerequisites": ["T01"]},
    ):
        assert client.post("/admin/topics", json=t, headers=admin_headers).status_code == 201
    ids = {}
    spec = (("A1", "T01", 1), ("A2", "T01", 2), ("A3", "T01", 3), ("B1", "T02", 1))
    for code, topic, diff in spec:
        r = client.post(
            "/admin/problems", json=_problem(topic, diff, "1", code), headers=admin_headers
        )
        assert r.status_code == 201
        ids[code] = r.json()["id"]
    return ids


def test_next_starts_with_base_topic_and_matching_level(client, student_headers, bank):
    r = client.get("/next", headers=student_headers)
    assert r.status_code == 200
    body = r.json()
    # prior 0.667 → түвшин 2 → A2
    assert body["topic_id"] == "T01"
    assert body["problem"]["code"] == "A2"
    assert body["target_difficulty"] == 2
    assert "Суурь" in body["reason"]
    assert "answers" not in body["problem"]


def test_next_skips_solved_and_moves_to_next_topic(client, student_headers, bank):
    # A2-г бодно → T01 mastery өснө, A2 дахин санал болохгүй
    client.post(f"/problems/{bank['A2']}/attempt", json={"answer": "1"}, headers=student_headers)
    body = client.get("/next", headers=student_headers).json()
    assert body["topic_id"] == "T01" and body["problem"]["code"] != "A2"

    # T01-ийг бүрэн эзэмшүүлье (≥0.95) → T02 нээгдэнэ
    for code in ("A1", "A3"):
        client.post(
            f"/problems/{bank[code]}/attempt", json={"answer": "1"}, headers=student_headers
        )
    m = {x["topic_id"]: x for x in client.get("/me/mastery", headers=student_headers).json()}
    assert m["T01"]["mastered"] is True
    body = client.get("/next", headers=student_headers).json()
    assert body["topic_id"] == "T02" and body["problem"]["code"] == "B1"
    assert "Суурь" in body["reason"]  # урьдач сэдвийн нэр шалтгаанд

    # T02-т ганц бодлого: бодсон ч (<0.95) дахин санал болгоно
    client.post(f"/problems/{bank['B1']}/attempt", json={"answer": "1"}, headers=student_headers)
    body = client.get("/next", headers=student_headers).json()
    assert body["topic_id"] == "T02" and body["problem"]["code"] == "B1"


def test_next_all_mastered_is_review(client, student_headers, db_session, bank):
    from app.models.learning import Mastery
    from app.models.user import User

    uid = db_session.scalar(select(User.id).where(User.email == "student@test.mn"))
    db_session.add(Mastery(user_id=uid, topic_id="T01", p_mastery=0.99))
    db_session.add(Mastery(user_id=uid, topic_id="T02", p_mastery=0.96))
    db_session.commit()
    body = client.get("/next", headers=student_headers).json()
    assert "давтлага" in body["reason"]
    assert body["topic_id"] == "T02"  # хамгийн бага mastery
    assert body["problem"]["code"] == "B1"


def test_next_with_chosen_topic(client, student_headers, bank):
    body = client.get("/next?topic_id=T02", headers=student_headers).json()
    assert body["topic_id"] == "T02" and body["problem"]["code"] == "B1"
    assert client.get("/next?topic_id=NOPE", headers=student_headers).status_code == 404


def test_next_without_problems(client, student_headers, admin_headers):
    client.post("/admin/topics", json={"id": "T09", "name": "Хоосон", "grade": 10},
                headers=admin_headers)
    body = client.get("/next", headers=student_headers).json()
    assert body["problem"] is None and body["topic_id"] == "T09"


def test_next_requires_login(client):
    assert client.get("/next").status_code == 401
