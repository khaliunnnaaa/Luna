"""Сурагчийн урсгал: бодлого → сануулга → хариу → mastery (FR-05, 06, 08, 10)."""

import pytest

from app.services.answer_checker import check_answer


@pytest.fixture()
def problem_id(client, admin_headers):
    assert client.post(
        "/admin/topics", json={"id": "T04", "name": "Квадрат тэгшитгэл", "grade": 10},
        headers=admin_headers,
    ).status_code == 201
    r = client.post(
        "/admin/problems",
        json={
            "topic_id": "T04",
            "difficulty": 1,
            "statement": "Тэгшитгэлийг бод: $x^2 - 7x + 12 = 0$",
            "answers": ["[3, 4]"],
            "hints": ["Үржвэрт задал", "Үржвэр нь 12, нийлбэр нь 7 болох хоёр тоо", "3 ба 4"],
            "terms": ["квадрат тэгшитгэл", "язгуур"],
        },
        headers=admin_headers,
    )
    assert r.status_code == 201
    client.post(
        "/admin/terms",
        json={"term": "язгуур", "explanation": "Тэгшитгэлийг хангах утга", "topic_id": "T04"},
        headers=admin_headers,
    )
    return r.json()["id"]


# ---------- Алдааны төрөл ----------
@pytest.mark.parametrize(
    "student, answers, expected",
    [
        ("3", ["3"], (True, None)),
        ("0.5", ["1/2"], (True, None)),
        ("[4, 3]", ["[3, 4]"], (True, None)),
        ("2x+2", ["2*(x+1)"], (True, None)),
        ("-3", ["3"], (False, "sign_error")),
        ("[3]", ["[3, 4]"], (False, "partial")),
        ("", ["3"], (False, "empty")),
        ("x==", ["3"], (False, "unparsable")),
        ("5", ["3"], (False, "wrong")),
        ("7", ["3", "7"], (True, None)),  # олон зөв хариу
    ],
)
def test_check_answer(student, answers, expected):
    assert check_answer(student, answers) == expected


# ---------- Бодлого харах ----------
def test_student_view_hides_answers_and_hints(client, student_headers, problem_id):
    r = client.get(f"/problems/{problem_id}", headers=student_headers)
    assert r.status_code == 200
    body = r.json()
    assert "answers" not in body and "hints" not in body
    assert body["hint_count"] == 3
    assert body["topic_name"] == "Квадрат тэгшитгэл"
    assert body["my_attempts"] == 0 and body["solved"] is False


def test_problem_requires_login(client, problem_id):
    assert client.get(f"/problems/{problem_id}").status_code == 401
    assert client.get("/problems/999999").status_code == 401


# ---------- Сануулга ----------
def test_hints_levels(client, student_headers, problem_id):
    r = client.get(f"/problems/{problem_id}/hints/1", headers=student_headers)
    assert r.status_code == 200 and r.json()["hint"] == "Үржвэрт задал"
    assert client.get(f"/problems/{problem_id}/hints/3", headers=student_headers).status_code == 200
    assert client.get(f"/problems/{problem_id}/hints/4", headers=student_headers).status_code == 404
    assert client.get(f"/problems/{problem_id}/hints/0", headers=student_headers).status_code == 404


# ---------- Хариу илгээх ----------
def test_attempt_flow_updates_mastery(client, student_headers, problem_id):
    before = {m["topic_id"]: m for m in client.get("/me/mastery", headers=student_headers).json()}
    assert before["T04"]["attempts_count"] == 0

    r = client.post(
        f"/problems/{problem_id}/attempt",
        json={"answer": "[3]", "hints_used": 1},
        headers=student_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["is_correct"] is False and body["error_type"] == "partial"
    assert body["mastery_after"] < body["mastery_before"]
    assert "3 ба 4" not in body["feedback"]  # зөв хариуг задруулахгүй

    r = client.post(
        f"/problems/{problem_id}/attempt",
        json={"answer": "[4, 3]", "hints_used": 2},
        headers=student_headers,
    )
    body = r.json()
    assert body["is_correct"] is True and body["error_type"] is None
    assert body["mastery_after"] > body["mastery_before"]
    assert body["attempts_on_problem"] == 2

    after = {m["topic_id"]: m for m in client.get("/me/mastery", headers=student_headers).json()}
    assert after["T04"]["attempts_count"] == 2 and after["T04"]["correct_count"] == 1

    p = client.get(f"/problems/{problem_id}", headers=student_headers).json()
    assert p["solved"] is True and p["my_attempts"] == 2

    hist = client.get("/me/attempts", headers=student_headers).json()
    assert [a["is_correct"] for a in hist] == [True, False]  # сүүлийнх эхэндээ
    assert hist[0]["hints_used"] == 2


def test_resolving_solved_problem_does_not_change_mastery(client, student_headers, problem_id):
    client.post(f"/problems/{problem_id}/attempt", json={"answer": "[3, 4]"},
                headers=student_headers)
    r = client.post(f"/problems/{problem_id}/attempt", json={"answer": "[3, 4]"},
                    headers=student_headers)
    body = r.json()
    assert body["is_correct"] is True
    assert body["mastery_before"] == body["mastery_after"]


def test_attempt_only_for_students(client, admin_headers, problem_id):
    r = client.post(f"/problems/{problem_id}/attempt", json={"answer": "3"}, headers=admin_headers)
    assert r.status_code == 403
    assert client.post(f"/problems/{problem_id}/attempt", json={"answer": "3"}).status_code == 401


def test_attempt_unknown_problem(client, student_headers):
    r = client.post("/problems/999999/attempt", json={"answer": "3"}, headers=student_headers)
    assert r.status_code == 404


# ---------- Нэр томьёо ----------
def test_terms_public_and_click(client, student_headers, problem_id):
    r = client.get("/terms")
    assert r.status_code == 200 and r.json()[0]["term"] == "язгуур"

    r = client.post("/term-clicks", json={"term": "язгуур", "problem_id": problem_id},
                    headers=student_headers)
    assert r.status_code == 201
    assert r.json()["explanation"] == "Тэгшитгэлийг хангах утга"

    # Толинд байхгүй үг ч бүртгэгдэнэ (сул талын дохио), тайлбар нь None
    r = client.post("/term-clicks", json={"term": "дискриминант"}, headers=student_headers)
    assert r.status_code == 201 and r.json()["explanation"] is None
    assert client.post("/term-clicks", json={"term": "x"}).status_code == 401
