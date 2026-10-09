"""FR-02: түвшин тогтоох adaptive тест."""

import pytest


@pytest.fixture()
def bank(client, admin_headers):
    """T01 ← T02 ← T03, сэдэв бүрт 1/2/3 түвшний бодлого (хариу бүгд 1)."""
    chain = [("T01", []), ("T02", ["T01"]), ("T03", ["T02"])]
    for tid, pre in chain:
        r = client.post(
            "/admin/topics",
            json={"id": tid, "name": f"Сэдэв {tid}", "grade": 10, "prerequisites": pre},
            headers=admin_headers,
        )
        assert r.status_code == 201
        for d in (1, 2, 3):
            r = client.post(
                "/admin/problems",
                json={
                    "code": f"{tid}-{d}",
                    "topic_id": tid,
                    "difficulty": d,
                    "statement": f"{tid} түвшин {d}: $x$",
                    "answers": ["1"],
                },
                headers=admin_headers,
            )
            assert r.status_code == 201


def test_state_none_before_start(client, student_headers):
    r = client.get("/placement", headers=student_headers)
    assert r.status_code == 200 and r.json()["status"] == "none"
    assert client.get("/placement").status_code == 401


def test_start_requires_topics(client, student_headers):
    assert client.post("/placement/start", headers=student_headers).status_code == 409


def test_adaptive_flow_sets_initial_mastery(client, student_headers, bank):
    st = client.post("/placement/start", headers=student_headers).json()
    assert st["status"] == "active" and st["total"] == 3 and st["index"] == 0
    q = st["question"]
    assert q["topic_id"] == "T01" and q["difficulty"] == 2  # суурь сэдвээс, 2-р түвшнээс
    assert "answers" not in q and 0 < st["seconds_left"] <= 600

    # 1) зөв → дараагийнх хүнд (3)
    r = client.post(
        "/placement/answer", json={"problem_id": q["problem_id"], "answer": "1"},
        headers=student_headers,
    ).json()
    assert r["correct"] is True
    q = r["state"]["question"]
    assert q["topic_id"] == "T02" and q["difficulty"] == 3 and r["state"]["index"] == 1

    # 2) буруу → хялбар (2)
    r = client.post(
        "/placement/answer", json={"problem_id": q["problem_id"], "answer": "7"},
        headers=student_headers,
    ).json()
    assert r["correct"] is False and r["error_type"] == "wrong"
    q = r["state"]["question"]
    assert q["topic_id"] == "T03" and q["difficulty"] == 2

    # 3) "мэдэхгүй" (хоосон) → буруу, тест дуусна
    r = client.post(
        "/placement/answer", json={"problem_id": q["problem_id"], "answer": ""},
        headers=student_headers,
    ).json()
    assert r["correct"] is False and r["error_type"] == "empty"
    st = r["state"]
    assert st["status"] == "done" and st["correct_count"] == 1
    by = {x["topic_id"]: x for x in st["result"]}
    assert by["T01"]["p_mastery"] == 0.75  # зөв, түвшин 2
    assert by["T02"]["p_mastery"] == 0.45  # буруу, түвшин 3
    assert by["T03"]["p_mastery"] == 0.30  # буруу, түвшин 2

    m = {x["topic_id"]: x for x in client.get("/me/mastery", headers=student_headers).json()}
    assert m["T01"]["p_mastery"] == 0.75 and m["T03"]["p_mastery"] == 0.3
    assert m["T01"]["attempts_count"] == 0  # placement нь оролдлогод тоологдохгүй

    # Дууссаны дараа GET нь үр дүнг буцаана; санал болгогч T01-ээс эхэлнэ (эзэмшээгүй)
    assert client.get("/placement", headers=student_headers).json()["status"] == "done"
    nxt = client.get("/next", headers=student_headers).json()
    assert nxt["topic_id"] == "T01" and nxt["target_difficulty"] == 2


def test_wrong_problem_id_and_no_session(client, student_headers, bank):
    r = client.post("/placement/answer", json={"problem_id": 1, "answer": "1"},
                    headers=student_headers)
    assert r.status_code == 404  # идэвхтэй тест алга
    client.post("/placement/start", headers=student_headers)
    r = client.post("/placement/answer", json={"problem_id": 999, "answer": "1"},
                    headers=student_headers)
    assert r.status_code == 409


def test_start_is_idempotent_and_finish_early(client, student_headers, bank):
    a = client.post("/placement/start", headers=student_headers).json()
    b = client.post("/placement/start", headers=student_headers).json()
    assert a["question"]["problem_id"] == b["question"]["problem_id"]
    pid = a["question"]["problem_id"]
    client.post(
        "/placement/answer", json={"problem_id": pid, "answer": "1"}, headers=student_headers
    )
    st = client.post("/placement/finish", headers=student_headers).json()
    assert st["status"] == "done" and len(st["result"]) == 1
    # Дахин эхлүүлбэл шинэ тест
    st = client.post("/placement/start", headers=student_headers).json()
    assert st["status"] == "active" and st["index"] == 0


def test_only_students_can_take_test(client, admin_headers, bank):
    assert client.post("/placement/start", headers=admin_headers).status_code == 403
