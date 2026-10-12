"""ML хэсгийн бодлогын санг (ml/csv/) Luna-гийн өгөгдлийн сан руу ачаална.

Эх сурвалж нь ML хэсэгтэй НЭГ (ml/csv/*.csv), тиймээс ангилагч, BKT, санал болгогч
ижил сэдвийн код (T01–T10), ижил бодлогын ID (T01-001 …) ашиглана.

Хэрэглээ (backend хавтсанд, venv идэвхтэй үед):
    python -m app.seed

Дахин ажиллуулахад давхардуулахгүй: ижил код/нэртэй мөрийг шинэчилнэ.
"""

import csv
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.database import SessionLocal, init_dev_db
from app.models.content import Problem, Term, Topic

CSV_DIR = Path(__file__).resolve().parents[2] / "ml" / "csv"


def _rows(path: Path) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:  # utf-8-sig: Excel-ийн BOM
        return [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def _split(value: str) -> List[str]:
    return [s.strip() for s in value.split(";") if s.strip()]


def seed_topics(db: Session, path: Path) -> int:
    rows = _rows(path)
    for r in rows:  # 1-р шат: сэдвүүд
        t = db.get(Topic, r["code"]) or Topic(id=r["code"])
        t.name, t.grade = r["name"], int(r["grade"] or 10)
        db.add(t)
    db.flush()
    for r in rows:  # 2-р шат: өмнөх сэдвийн холбоо (бүгд үүссэний дараа)
        prereqs = [db.get(Topic, p) for p in _split(r.get("prereq", ""))]
        db.get(Topic, r["code"]).prerequisites = [p for p in prereqs if p is not None]
    return len(rows)


def seed_terms(db: Session, path: Path) -> int:
    rows = _rows(path)
    for r in rows:
        t = db.scalar(select(Term).where(Term.term == r["term"])) or Term(term=r["term"])
        t.explanation, t.example = r["definition"], r.get("example") or None
        t.topic_id = r["topic"] if db.get(Topic, r.get("topic") or "") else None
        db.add(t)
    return len(rows)


def statement_of(text: str, latex: str) -> str:
    """Бодлогын текст + томьёо → "Тэгшитгэлийг бод. $x^2-7x+12=0$" (KaTeX-д харагдана)."""
    return f"{text} ${latex}$" if latex else text


def seed_problems(db: Session, path: Path) -> int:
    rows = _rows(path)
    for r in rows:
        p = db.scalar(select(Problem).where(Problem.code == r["id"])) or Problem(code=r["id"])
        p.topic_id = r["сэдэв_код"]
        p.subtopic = r.get("дэд_сэдэв") or None
        p.difficulty = int(r["түвшин(1-3)"])
        p.statement = statement_of(r["бодлогын_текст"], r["томьёо_LaTeX"])
        p.answers = [r["хариу_sympy"]]
        p.hints = [h for h in (r["сануулга_1"], r["сануулга_2"], r["сануулга_3"]) if h]
        steps = r.get("бодолтын_алхам", "").split("||")
        p.solution_steps = [st.strip() for st in steps if st.strip()]
        p.common_mistakes = r.get("түгээмэл_алдаа") or None
        p.terms = _split(r.get("нэр_томьёо", ""))
        p.source = "Бодлогын сан (capstone)"
        db.add(p)
    return len(rows)


def seed_all(db: Session, csv_dir: Path = CSV_DIR) -> Dict[str, int]:
    counts = {
        "topics": seed_topics(db, csv_dir / "topics.csv"),
        "terms": seed_terms(db, csv_dir / "glossary.csv"),
        "problems": seed_problems(db, csv_dir / "problems.csv"),
    }
    db.commit()
    return counts


def main() -> None:
    init_dev_db()
    with SessionLocal() as db:
        c = seed_all(db)
    print(f"Ачааллаа: {c['topics']} сэдэв, {c['terms']} нэр томьёо, {c['problems']} бодлого")


if __name__ == "__main__":
    main()
