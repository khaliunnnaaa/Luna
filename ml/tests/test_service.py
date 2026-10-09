"""ML HTTP сервисийн тест — загвар/OCR байхгүй үед ч зөв (503) хариулах ёстой."""
from fastapi.testclient import TestClient

import service
from conftest import needs_models

client = TestClient(service.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and set(body) == {"status", "classifier", "ocr"}


@needs_models
def test_classify():
    r = client.post("/classify", json={"text": "Тэгшитгэлийг бод. x^2-7x+12=0"})
    assert r.status_code == 200
    body = r.json()
    assert body["topic"] == "T04" and body["difficulty"] in (1, 2, 3)
    assert 0 < body["confidence"] <= 1 and isinstance(body["subtopics"], list)


def test_classify_validation():
    assert client.post("/classify", json={"text": ""}).status_code == 422


def test_ocr_unavailable_or_rejects_bad_type(monkeypatch):
    monkeypatch.setattr(service, "_ocr_ready", lambda: False)
    r = client.post("/ocr", files={"file": ("a.jpg", b"xx", "image/jpeg")})
    assert r.status_code == 503
    monkeypatch.setattr(service, "_ocr_ready", lambda: True)
    r = client.post("/ocr", files={"file": ("a.gif", b"xx", "image/gif")})
    assert r.status_code == 415
