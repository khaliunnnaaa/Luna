"""FR-07: ижил төстэй бодлогоор тайлбарлах."""

import pytest

from app.services import ml_client


def _p(code, topic, sub, diff, steps):
    return {
        "code": code, "topic_id": topic, "subtopic": sub, "difficulty": diff,
        "statement": f"{code}: $x$", "answers": ["1"], "hints": ["h"], "solution_steps": steps,
    }


@pytest.fixture()
def bank(client, admin_headers):
    client.post("/admin/topics", json={"id": "T04", "name": "Квадрат тэгшитгэл", "grade": 10},
                headers=admin_headers)
    client.post("/admin/topics", json={"id": "T05", "name": "Тэнцэтгэл биш", "grade": 10},
                headers=admin_headers)
    ids = {}
    for code, topic, sub, diff, steps in (
        ("A", "T04", "Виетийн теорем", 1, ["Виет", "$x = 3$"]),
        ("B", "T04", "Дискриминант", 2, ["D", "$x = \\frac{1}{2}$"]),
        ("C", "T04", "Дискриминант", 3, []),  # алхамгүй → сонгогдохгүй
        ("E", "T05", "Шугаман", 1, ["ш"]),
    ):
        r = client.post("/admin/problems", json=_p(code, topic, sub, diff, steps),
                        headers=admin_headers)
        assert r.status_code == 201, r.text
        ids[code] = r.json()["id"]
    return ids


def test_similar_prefers_ml_subtopic_and_difficulty(client, student_headers, bank, monkeypatch):
    monkeypatch.setattr(ml_client, "classify", lambda t: {
        "topic": "T04", "difficulty": 2, "confidence": 0.9, "subtopics": ["Дискриминант"]})
    r = client.post("/similar", json={"text": "2x^2+3x-2=0"}, headers=student_headers)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["code"] == "B" and b["topic_name"] == "Квадрат тэгшитгэл"
    assert b["steps"] == ["D", "$x = \\frac{1}{2}$"] and b["ml_available"] is True
    assert "Дискриминант" in b["reason"]
    # "өөр жишээ": B-г хасвал алхамтай үлдсэн нь A (C алхамгүй)
    r = client.post("/similar", json={"text": "2x^2+3x-2=0", "exclude": [bank["B"]]},
                    headers=student_headers)
    assert r.json()["code"] == "A"


def test_similar_without_ml_needs_topic(client, student_headers, bank, monkeypatch):
    monkeypatch.setattr(ml_client, "classify", lambda t: None)
    r = client.post("/similar", json={"text": "x^2=1"}, headers=student_headers)
    assert r.status_code == 400
    r = client.post("/similar", json={"text": "x^2=1", "topic_id": "T04"}, headers=student_headers)
    assert r.status_code == 200 and r.json()["ml_available"] is False
    assert r.json()["code"] == "B"  # түвшин анхдагч 2-т хамгийн ойр
    r = client.post("/similar", json={"topic_id": "NOPE"}, headers=student_headers)
    assert r.status_code == 404


def test_similar_no_steps_in_topic(client, student_headers, admin_headers, monkeypatch):
    monkeypatch.setattr(ml_client, "classify", lambda t: None)
    client.post("/admin/topics", json={"id": "T09", "name": "Триг", "grade": 11},
                headers=admin_headers)
    r = client.post("/similar", json={"topic_id": "T09"}, headers=student_headers)
    assert r.status_code == 404


def test_student_view_never_exposes_steps(client, student_headers, bank):
    r = client.get(f"/problems/{bank['B']}", headers=student_headers)
    assert "solution_steps" not in r.json() and "steps" not in r.json()


def test_upload_outcome(client, student_headers, monkeypatch, tmp_path):
    from app.services import storage

    monkeypatch.setattr(storage, "_storage", storage.LocalStorage(str(tmp_path)))
    monkeypatch.setattr(ml_client, "ocr", lambda d, c: None)
    monkeypatch.setattr(ml_client, "classify", lambda t: None)
    u = client.post("/uploads", files={"file": ("p.png", b"\x89PNG" + b"\x00" * 16, "image/png")},
                    headers=student_headers).json()
    r = client.post(f"/uploads/{u['id']}/outcome", json={"solved": True}, headers=student_headers)
    assert r.status_code == 200 and r.json()["outcome"] == "solved"
    r = client.post(f"/uploads/{u['id']}/outcome", json={"solved": False}, headers=student_headers)
    assert r.json()["outcome"] == "unsolved"


def test_admin_steps_validation(client, admin_headers, bank):
    bad = _p("Z", "T04", None, 1, [f"алхам {i}" for i in range(13)])
    assert client.post("/admin/problems", json=bad, headers=admin_headers).status_code == 422
