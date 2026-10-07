"""Бүх модульд хэрэглэгдэх зам, өгөгдөл ачаалах туслах функцууд."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
RAW_DIR = ROOT / "data" / "raw"
STATE_DIR = ROOT / "state"
BANK_PATH = ROOT / "бодлогын_сан.xlsx"

SEED = 42

# бодлогын_сан.xlsx-ийн "Бодлого" хуудасны баганын нэрс (файлаас уншиж тогтоосон)
BANK_SHEET = "Бодлого"
COL_ID = "id"
COL_TOPIC = "сэдэв_код"
COL_SUBTOPIC = "дэд_сэдэв"
COL_DIFFICULTY = "түвшин(1-3)"
COL_TEXT = "бодлогын_текст"
COL_LATEX = "томьёо_LaTeX"

MASTERY_THRESHOLD = 0.95


@dataclass
class Topic:
    code: str
    name: str
    grade: int
    prereq: list[str] = field(default_factory=list)


def load_topics(path: Path | None = None) -> dict[str, Topic]:
    """config/topics.csv-ийг уншина. prereq багана ";"-ээр тусгаарлагдсан."""
    path = path or CONFIG_DIR / "topics.csv"
    topics: dict[str, Topic] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            prereq = [p.strip() for p in (row["prereq"] or "").split(";") if p.strip()]
            topics[row["code"]] = Topic(row["code"], row["name"], int(row["grade"]), prereq)
    return topics


def problem_input(text: str | None, latex: str | None) -> str:
    """Ангилагчийн оролт: бодлогын текст + LaTeX томьёо нэг мөрөнд."""
    return " ".join(s.strip() for s in (text, latex) if isinstance(s, str) and s.strip())


def load_bank(path: Path | None = None) -> pd.DataFrame:
    """Бодлогын санг уншиж, хоосон мөрийг хасна. `input` баганыг нэмнэ."""
    df = pd.read_excel(path or BANK_PATH, sheet_name=BANK_SHEET)
    df = df.dropna(how="all")
    df = df.dropna(subset=[COL_ID, COL_TOPIC])
    df = df[df[COL_ID].astype(str).str.strip() != ""].copy()
    df[COL_DIFFICULTY] = df[COL_DIFFICULTY].astype(int)
    df["input"] = [problem_input(t, l) for t, l in zip(df[COL_TEXT], df[COL_LATEX])]
    return df.reset_index(drop=True)
