"""FR-03/04: зураг оруулах, OCR, ангилал — ML сервисийг monkeypatch-аар орлуулна."""

import pytest

from app.services import ml_client, storage

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture(autouse=True)
def local_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_storage", storage.LocalStorage(str(tmp_path)))
    yield


@pytest.fixture()
def topic(client, admin_headers):
    client.post("/admin/topics", json={"id": "T04", "name": "Квадрат тэгшитгэл", "grade": 10},
                headers=admin_headers)
    client.post("/admin/terms", json={"term": "дискриминант", "explanation": "D = b² − 4ac",
                                      "topic_id": "T04"}, headers=admin_headers)


@pytest.fixture()
def ml_up(monkeypatch):
    ocr = {"text": "Тэгшитгэлийг бод.", "latex": ["x^2-7x+12=0"]}
    clf = {"topic": "T04", "difficulty": 2, "confidence": 0.9, "subtopics": ["Виет"]}
    monkeypatch.setattr(ml_client, "ocr", lambda data, ct: ocr)
    monkeypatch.setattr(ml_client, "classify", lambda text: clf)


@pytest.fixture()
def ml_down(monkeypatch):
    monkeypatch.setattr(ml_client, "ocr", lambda data, ct: None)
    monkeypatch.setattr(ml_client, "classify", lambda text: None)


def _upload(client, headers, content=PNG, name="p.png", ct="image/png"):
    return client.post("/uploads", files={"file": (name, content, ct)}, headers=headers)


def test_upload_with_ml(client, student_headers, topic, ml_up):
    r = _upload(client, student_headers)
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["status"] == "done" and b["ml_available"] is True
    assert b["ocr_text"] == "Тэгшитгэлийг бод." and b["ocr_latex"] == "x^2-7x+12=0"
    assert b["edited_text"] == "Тэгшитгэлийг бод. x^2-7x+12=0"
    assert b["predicted_topic"] == "T04" and b["topic_name"] == "Квадрат тэгшитгэл"

    img = client.get(f"/uploads/{b['id']}/image", headers=student_headers)
    assert img.status_code == 200 and img.content == PNG
    assert img.headers["content-type"] == "image/png"
    assert [u["id"] for u in client.get("/uploads", headers=student_headers).json()] == [b["id"]]


def test_upload_without_ml_falls_back_to_manual(client, student_headers, topic, ml_down):
    r = _upload(client, student_headers)
    assert r.status_code == 201
    b = r.json()
    assert b["status"] == "failed" and b["ml_available"] is False and "гараар" in b["message"]
    assert b["edited_text"] is None

    # гараар бичвэл ашиглах боломжтой болно (ML одоо ч байхгүй)
    r = client.put(f"/uploads/{b['id']}", json={"edited_text": "x^2 = 4"}, headers=student_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "done" and r.json()["edited_text"] == "x^2 = 4"
    assert r.json()["predicted_topic"] is None


def test_edit_reclassifies(client, student_headers, topic, ml_up, monkeypatch):
    b = _upload(client, student_headers).json()
    clf = {"topic": "T04", "difficulty": 1, "confidence": 0.5, "subtopics": []}
    monkeypatch.setattr(ml_client, "classify", lambda text: clf)
    r = client.put(
        f"/uploads/{b['id']}", json={"edited_text": "x^2 - 9 = 0"}, headers=student_headers
    )
    assert r.json()["edited_text"] == "x^2 - 9 = 0" and r.json()["predicted_topic"] == "T04"


def test_delete_removes_file_and_row(client, student_headers, topic, ml_up):
    b = _upload(client, student_headers).json()
    assert client.delete(f"/uploads/{b['id']}", headers=student_headers).status_code == 204
    assert client.get(f"/uploads/{b['id']}", headers=student_headers).status_code == 404
    assert client.get("/uploads", headers=student_headers).json() == []


def test_upload_validation_and_ownership(client, student_headers, admin_headers, topic, ml_up):
    assert _upload(client, student_headers, ct="image/gif", name="a.gif").status_code == 415
    assert _upload(client, student_headers, content=b"").status_code == 400
    assert client.post("/uploads", files={"file": ("p.png", PNG, "image/png")}).status_code == 401
    b = _upload(client, student_headers).json()
    # өөр хэрэглэгч харж чадахгүй
    assert client.get(f"/uploads/{b['id']}", headers=admin_headers).status_code == 404
    assert client.delete(f"/uploads/{b['id']}", headers=admin_headers).status_code == 404


def test_classify_text(client, student_headers, topic, ml_up):
    r = client.post("/classify", json={"text": "Дискриминант ашиглан бод: x^2-7x+12=0"},
                    headers=student_headers)
    assert r.status_code == 200
    b = r.json()
    assert b["available"] and b["topic_id"] == "T04" and b["topic_name"] == "Квадрат тэгшитгэл"
    assert b["terms"] == ["дискриминант"]


def test_classify_without_ml(client, student_headers, topic, ml_down):
    b = client.post("/classify", json={"text": "x^2 = 1"}, headers=student_headers).json()
    assert b["available"] is False and b["topic_id"] is None


def test_local_storage_rejects_traversal(tmp_path):
    s = storage.LocalStorage(str(tmp_path))
    with pytest.raises(ValueError):
        s.load("../etc/passwd")
