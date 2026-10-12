"""FR-14: эцэг эх ↔ хүүхэд холбох, хүүхдийн тайлан, зөвлөмж."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models.learning import LinkCode
from app.models.user import Role
from app.services.parent_report import build_report
from tests.conftest import _headers_for

NOW = datetime(2026, 10, 12, 4, 0, tzinfo=timezone.utc)  # УБ-ын цагаар 12:00


def _att(days_ago, correct, topic="T01", before=0.3, after=0.4, err=None, hints=0, hour=4):
    t = NOW - timedelta(days=days_ago)
    return SimpleNamespace(
        created_at=t.replace(hour=hour),
        is_correct=correct,
        topic_id=topic,
        mastery_before=before,
        mastery_after=after,
        error_type=None if correct else (err or "wrong"),
        hints_used=hints,
    )


def _mastery(p1=0.4, p2=0.2, mastered2=False):
    return [
        {
            "topic_id": "T01",
            "name": "Зэрэг",
            "grade": 10,
            "p_mastery": p1,
            "attempts_count": 3,
            "correct_count": 1,
            "mastered": p1 >= 0.95,
            "prerequisites": [],
        },
        {
            "topic_id": "T02",
            "name": "Илэрхийлэл",
            "grade": 10,
            "p_mastery": p2,
            "attempts_count": 0,
            "correct_count": 0,
            "mastered": mastered2,
            "prerequisites": ["T01"],
        },
    ]


# ---------- build_report (цэвэр функц) ----------
def test_empty_child_gets_start_tips():
    r = build_report("Бат", [], _mastery(), NOW, placement_done=False)
    assert r["summary"]["attempts_total"] == 0 and r["summary"]["accuracy_7d"] is None
    assert len(r["activity"]) == 14 and all(d["correct"] == d["wrong"] == 0 for d in r["activity"])
    assert len(r["trend"]) == 30
    assert [t["kind"] for t in r["tips"]] == ["start", "start"]


def test_activity_buckets_by_ulaanbaatar_day():
    # UTC 17:00 = УБ-ын дараагийн өдрийн 01:00 → өнөөдөр (days_ago=1 + 8 цаг) гэж тоологдоно
    a = [_att(1, True, hour=17), _att(0, False, err="sign_error"), _att(3, True)]
    r = build_report("Бат", a, _mastery(), NOW, placement_done=True)
    today, yesterday = r["activity"][-1], r["activity"][-2]
    assert today["date"] == "2026-10-12" and (today["correct"], today["wrong"]) == (1, 1)
    assert (yesterday["correct"], yesterday["wrong"]) == (0, 0)
    assert r["summary"]["attempts_7d"] == 3 and r["summary"]["correct_7d"] == 2
    assert r["summary"]["active_days_14"] == 2


def test_trend_starts_from_first_mastery_before_and_follows_after():
    a = [_att(5, True, before=0.30, after=0.50), _att(2, True, before=0.50, after=0.70)]
    r = build_report("Бат", a, _mastery(p1=0.70, p2=0.20), NOW, placement_done=True)
    by_date = {p["date"]: p["avg_mastery"] for p in r["trend"]}
    assert by_date["2026-09-13"] == pytest.approx((0.30 + 0.20) / 2)  # оролдлогоос өмнө
    assert by_date["2026-10-07"] == pytest.approx((0.50 + 0.20) / 2)
    assert by_date["2026-10-12"] == pytest.approx((0.70 + 0.20) / 2)


def test_tips_inactivity_error_focus_and_hints():
    a = [_att(6, False, err="sign_error", hints=3), _att(5, False, err="sign_error", hints=2)]
    r = build_report("Бат", a, _mastery(p1=0.4), NOW, placement_done=True)
    kinds = [t["kind"] for t in r["tips"]]
    assert kinds == ["habit", "focus", "error", "hints"]
    assert r["focus"][0]["name"] == "Зэрэг" and r["focus"][0]["accuracy"] == pytest.approx(
        1 / 3, abs=1e-3
    )
    assert r["errors"][0] == {"type": "sign_error", "label": "Тэмдгийн алдаа", "count": 2}


def test_focus_names_weak_prerequisite():
    m = _mastery(p1=0.4, p2=0.3)
    m[1]["attempts_count"] = 2
    r = build_report("Бат", [_att(0, False)], m, NOW, placement_done=True)
    assert r["focus"][0]["topic_id"] == "T02" and r["focus"][0]["weak_prerequisites"] == ["Зэрэг"]
    assert "«Зэрэг»" in r["tips"][0]["text"]


def test_praise_when_accurate():
    a = [_att(d, True) for d in range(5)]
    r = build_report("Бат", a, _mastery(), NOW, placement_done=True)
    assert r["tips"][-1]["kind"] == "praise" and "100%" in r["tips"][-1]["text"]


# ---------- API ----------
@pytest.fixture()
def parent_headers(client, db_session):
    return _headers_for(client, db_session, "parent@test.mn", Role.parent)


def _link(client, student_headers, parent_headers):
    code = client.post("/me/link-code", headers=student_headers).json()["code"]
    return client.post("/parent/children", json={"code": code}, headers=parent_headers)


def test_link_flow_and_report(client, student_headers, parent_headers):
    r = _link(client, student_headers, parent_headers)
    assert r.status_code == 200
    child_id = r.json()["id"]
    assert [c["id"] for c in client.get("/parent/children", headers=parent_headers).json()] == [
        child_id
    ]
    assert len(client.get("/me/parents", headers=student_headers).json()) == 1

    rep = client.get(f"/parent/children/{child_id}/report", headers=parent_headers)
    assert rep.status_code == 200
    body = rep.json()
    assert body["child"]["id"] == child_id
    assert len(body["activity"]) == 14 and len(body["trend"]) == 30
    assert body["tips"][0]["kind"] == "start"  # тест өгөөгүй


def test_code_is_single_use_and_case_insensitive(
    client, db_session, student_headers, parent_headers
):
    code = client.post("/me/link-code", headers=student_headers).json()["code"]
    assert len(code) == 6
    other = _headers_for(client, db_session, "parent2@test.mn", Role.parent)
    assert (
        client.post(
            "/parent/children", json={"code": code.lower()}, headers=parent_headers
        ).status_code
        == 200
    )
    assert client.post("/parent/children", json={"code": code}, headers=other).status_code == 400


def test_expired_code_rejected(client, db_session, student_headers, parent_headers):
    code = client.post("/me/link-code", headers=student_headers).json()["code"]
    lc = db_session.get(LinkCode, code)
    lc.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    assert (
        client.post("/parent/children", json={"code": code}, headers=parent_headers).status_code
        == 400
    )


def test_new_code_replaces_old(client, student_headers, parent_headers):
    old = client.post("/me/link-code", headers=student_headers).json()["code"]
    client.post("/me/link-code", headers=student_headers)
    assert (
        client.post("/parent/children", json={"code": old}, headers=parent_headers).status_code
        == 400
    )


def test_other_parent_cannot_see_child(client, db_session, student_headers, parent_headers):
    child_id = _link(client, student_headers, parent_headers).json()["id"]
    stranger = _headers_for(client, db_session, "stranger@test.mn", Role.parent)
    assert client.get(f"/parent/children/{child_id}/report", headers=stranger).status_code == 404


def test_student_can_unlink_parent(client, student_headers, parent_headers):
    child_id = _link(client, student_headers, parent_headers).json()["id"]
    pid = client.get("/me/parents", headers=student_headers).json()[0]["id"]
    assert client.delete(f"/me/parents/{pid}", headers=student_headers).status_code == 204
    assert (
        client.get(f"/parent/children/{child_id}/report", headers=parent_headers).status_code == 404
    )


def test_roles_are_enforced(client, student_headers, parent_headers):
    assert client.get("/parent/children", headers=student_headers).status_code == 403
    assert client.post("/me/link-code", headers=parent_headers).status_code == 403
