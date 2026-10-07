"""Сурагчийн сэдэв бүрийн эзэмшлийг (mastery) BKT томьёогоор шинэчилнэ.

Төлөвийг одоогоор энгийн JSON файлд хадгална (state/students/<id>.json). Хадгалах хэсгийг
`StudentStore` интерфейсээр тусгаарласан тул дараа нь өгөгдлийн сан руу шилжүүлэхэд зөвхөн
шинэ store класс бичихэд хангалттай.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import yaml

from ml.common import CONFIG_DIR, STATE_DIR, load_topics


EPS = 1e-4

# ---------------------------------------------------------------- BKT параметр
@lru_cache(maxsize=1)
def load_bkt_params(path: Path | None = None) -> dict[str, dict[str, float]]:
    """config/bkt_params.yaml-аас сэдэв бүрийн {prior, learn, guess, slip}."""
    path = path or CONFIG_DIR / "bkt_params.yaml"
    if not path.exists():
        raise FileNotFoundError(f"{path} алга. Эхлээд: python -m ml.tracing.train_bkt")
    cfg = yaml.safe_load(open(path, encoding="utf-8"))
    default = cfg["default"]
    return {code: {**default, **cfg.get("topics", {}).get(code, {})} for code in load_topics()}


def bkt_update(p_mastery: float, correct: bool, learn: float, guess: float, slip: float) -> float:
    """Нэг хариултын дараах BKT шинэчлэл.

    1) Ажиглалтаар нөхцөлдүүлсэн (posterior) магадлал:
         зөв:   p(1-s) / [p(1-s) + (1-p)g]
         буруу: p s    / [p s    + (1-p)(1-g)]
    2) Суралцах шилжилт:  p' = post + (1 - post) * learn

    Үр дүнг [EPS, 1−EPS] завсарт хязгаарлана: яг 1.0 болчихвол дараагийн буруу хариулт
    p·s / (p·s + 0) = 1 болж mastery цаашид хэзээ ч буурахгүй гацна.
    """
    p = p_mastery
    if correct:
        post = p * (1 - slip) / (p * (1 - slip) + (1 - p) * guess)
    else:
        post = p * slip / (p * slip + (1 - p) * (1 - guess))
    return min(max(post + (1 - post) * learn, EPS), 1 - EPS)


# ---------------------------------------------------------------- хадгалалт
class StudentStore:
    """Сурагчийн төлөв хадгалах интерфейс. Өгөгдлийн сан руу шилжихдээ үүнийг өвлөнө."""

    def load(self, student_id: str) -> dict | None:
        raise NotImplementedError

    def save(self, student_id: str, state: dict) -> None:
        raise NotImplementedError


class JSONStudentStore(StudentStore):
    def __init__(self, directory: Path | None = None):
        self.directory = Path(directory or STATE_DIR / "students")

    def _path(self, student_id: str) -> Path:
        if not re.fullmatch(r"[\w\-.@]+", student_id):
            raise ValueError(f"Буруу student_id: {student_id!r}")
        return self.directory / f"{student_id}.json"

    def load(self, student_id: str) -> dict | None:
        path = self._path(student_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def save(self, student_id: str, state: dict) -> None:
        path = self._path(student_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)  # бичих үед тасарвал файл эвдрэхгүй


def new_state(student_id: str, grade: int = 10) -> dict:
    params = load_bkt_params()
    return {
        "student_id": student_id,
        "grade": grade,
        "mastery": {code: p["prior"] for code, p in params.items()},
        "history": [],          # [{"topic", "correct", "problem_id", "time"}]
        "recommended": [],      # санал болгосон бодлогын id-ууд (давтахгүйн тулд)
    }


def get_state(student_id: str, store: StudentStore | None = None, grade: int = 10) -> dict:
    store = store or JSONStudentStore()
    return store.load(student_id) or new_state(student_id, grade)


def update_mastery(student_id: str, topic: str, correct: bool, problem_id: str | None = None,
                   store: StudentStore | None = None) -> dict[str, float]:
    """Хариултыг бүртгэж, тухайн сэдвийн mastery-г шинэчилнэ. Бүх сэдвийн mastery-г буцаана."""
    params = load_bkt_params()
    if topic not in params:
        raise ValueError(f"Үл мэдэгдэх сэдэв: {topic}")
    store = store or JSONStudentStore()
    state = get_state(student_id, store)
    p = params[topic]
    state["mastery"][topic] = bkt_update(state["mastery"][topic], bool(correct), p["learn"], p["guess"], p["slip"])
    state["history"].append({"topic": topic, "correct": bool(correct), "problem_id": problem_id,
                             "time": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    store.save(student_id, state)
    return {k: round(v, 4) for k, v in state["mastery"].items()}
