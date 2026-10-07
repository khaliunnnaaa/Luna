"""FR-16 контент удирдлагын тест."""

import pytest

from app.services.topic_graph import creates_cycle


def topic(id, prereqs=(), **kw):
    return {"id": id, "name": kw.get("name", id), "grade": 10, "prerequisites": list(prereqs)}


def problem(**kw):
    base = {
        "topic_id": "linear_eq",
        "difficulty": 2,
        "statement": "Бод: $2x + 4 = 10$",
        "answers": ["3"],
        "hints": ["x-ийг ганцаараа үлдээ", "4-ийг хасаад үз", "2x = 6"],
    }
    return {**base, **kw}


@pytest.fixture()
def topics(client, admin_headers):
    for t in [topic("linear_eq"), topic("factoring", ["linear_eq"])]:
        assert client.post("/admin/topics", json=t, headers=admin_headers).status_code == 201


# ---------- Эрх ----------
def test_admin_routes_require_admin(client, student_headers):
    assert client.get("/admin/topics").status_code == 401
    assert client.get("/admin/topics", headers=student_headers).status_code == 403
    r = client.post("/admin/topics", json=topic("x_topic"), headers=student_headers)
    assert r.status_code == 403


def test_public_topics_open(client, topics):
    r = client.get("/topics")
    assert r.status_code == 200
    assert {t["id"] for t in r.json()} == {"linear_eq", "factoring"}


# ---------- Сэдэв ----------
def test_topic_crud(client, admin_headers, topics):
    r = client.post("/admin/topics", json=topic("quadratic_eq", ["linear_eq", "factoring"]),
                    headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["prerequisites"] == ["factoring", "linear_eq"]

    r = client.put("/admin/topics/quadratic_eq", json=topic("quadratic_eq", ["factoring"],
                   name="Квадрат тэгшитгэл"), headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Квадрат тэгшитгэл"
    assert r.json()["prerequisites"] == ["factoring"]

    assert client.delete("/admin/topics/quadratic_eq", headers=admin_headers).status_code == 204


def test_topic_bad_id(client, admin_headers):
    r = client.post("/admin/topics", json=topic("Квадрат"), headers=admin_headers)
    assert r.status_code == 422


def test_topic_duplicate(client, admin_headers, topics):
    r = client.post("/admin/topics", json=topic("linear_eq"), headers=admin_headers)
    assert r.status_code == 409


def test_unknown_prerequisite(client, admin_headers):
    r = client.post("/admin/topics", json=topic("abc", ["nope"]), headers=admin_headers)
    assert r.status_code == 400


def test_cycle_rejected(client, admin_headers, topics):
    # factoring → linear_eq байгаа үед linear_eq → factoring нэмбэл тойрог
    r = client.put("/admin/topics/linear_eq", json=topic("linear_eq", ["factoring"]),
                   headers=admin_headers)
    assert r.status_code == 400
    assert "Тойрог" in r.json()["detail"]


def test_self_prerequisite_rejected(client, admin_headers, topics):
    r = client.put("/admin/topics/linear_eq", json=topic("linear_eq", ["linear_eq"]),
                   headers=admin_headers)
    assert r.status_code == 400


def test_cannot_delete_topic_with_dependents_or_problems(client, admin_headers, topics):
    assert client.delete("/admin/topics/linear_eq", headers=admin_headers).status_code == 409
    client.post("/admin/problems", json=problem(topic_id="factoring"), headers=admin_headers)
    assert client.delete("/admin/topics/factoring", headers=admin_headers).status_code == 409


def test_creates_cycle_helper():
    graph = {"b": ["a"], "c": ["b"]}
    assert creates_cycle(graph, "a", ["c"])
    assert not creates_cycle(graph, "d", ["c"])


# ---------- Бодлого ----------
def test_problem_crud(client, admin_headers, topics):
    r = client.post("/admin/problems", json=problem(code="q-1"), headers=admin_headers)
    assert r.status_code == 201
    pid = r.json()["id"]

    r = client.get("/admin/problems?topic_id=linear_eq", headers=admin_headers)
    assert [p["id"] for p in r.json()] == [pid]
    assert client.get("/admin/problems?topic_id=factoring", headers=admin_headers).json() == []

    r = client.put(f"/admin/problems/{pid}", json=problem(code="q-1", difficulty=3),
                   headers=admin_headers)
    assert r.json()["difficulty"] == 3

    assert client.delete(f"/admin/problems/{pid}", headers=admin_headers).status_code == 204
    assert client.get(f"/admin/problems/{pid}", headers=admin_headers).status_code == 404


def test_problem_validation(client, admin_headers, topics):
    bad = [
        problem(answers=[]),  # хариугүй
        problem(answers=["2x+"]),  # SymPy уншихгүй
        problem(hints=["1", "2", "3", "4"]),  # 3-аас олон сануулга
        problem(difficulty=4),  # 1–3 л зөвшөөрнө
    ]
    for p in bad:
        assert client.post("/admin/problems", json=p, headers=admin_headers).status_code == 422


def test_problem_unknown_topic(client, admin_headers, topics):
    r = client.post("/admin/problems", json=problem(topic_id="nope"), headers=admin_headers)
    assert r.status_code == 400


def test_problem_duplicate_code(client, admin_headers, topics):
    client.post("/admin/problems", json=problem(code="q-1"), headers=admin_headers)
    r = client.post("/admin/problems", json=problem(code="q-1"), headers=admin_headers)
    assert r.status_code == 409


# ---------- Нэр томьёо ----------
def test_term_crud(client, admin_headers, topics):
    data = {"term": "коэффициент", "explanation": "Хувьсагчийн өмнөх тоо", "topic_id": "linear_eq"}
    r = client.post("/admin/terms", json=data, headers=admin_headers)
    assert r.status_code == 201
    tid = r.json()["id"]
    assert client.post("/admin/terms", json=data, headers=admin_headers).status_code == 409

    r = client.put(f"/admin/terms/{tid}", json={**data, "example": "2x-ийн коэффициент 2"},
                   headers=admin_headers)
    assert r.json()["example"] == "2x-ийн коэффициент 2"
    assert client.delete(f"/admin/terms/{tid}", headers=admin_headers).status_code == 204


# ---------- ML-тэй нийцэх ----------
def test_ml_style_ids_and_answers(client, admin_headers):
    r = client.post("/admin/topics", json=topic("T01"), headers=admin_headers)
    assert r.status_code == 201
    body = problem(
        topic_id="T01",
        subtopic="Систем",
        answers=["{x: 7, y: 3}"],
        common_mistakes="x, y-ийг сольж бичих",
        terms=["систем", "систем", " "],
    )
    r = client.post("/admin/problems", json=body, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["terms"] == ["систем"]
    assert r.json()["subtopic"] == "Систем"


# ---------- Seed (ml/csv) ----------
def test_seed_from_ml_csv(db_session):
    from app import seed
    from app.models.content import Problem, Term, Topic
    from app.services.answer_checker import can_parse

    counts = seed.seed_all(db_session)
    assert counts == {
        "topics": db_session.query(Topic).count(),
        "terms": db_session.query(Term).count(),
        "problems": db_session.query(Problem).count(),
    }
    assert counts["topics"] == 10 and counts["problems"] >= 60

    p = db_session.query(Problem).filter_by(code="T04-021").one()
    assert p.topic_id == "T04" and 1 <= p.difficulty <= 3
    assert "$" in p.statement and len(p.hints) == 3
    assert all(can_parse(a) for q in db_session.query(Problem) for a in q.answers)

    t04 = db_session.get(Topic, "T04")
    assert [t.id for t in t04.prerequisites] == ["T03"]

    # Дахин ачаалахад давхардахгүй
    assert seed.seed_all(db_session) == counts
    assert db_session.query(Problem).count() == counts["problems"]
