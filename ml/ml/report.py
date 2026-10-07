"""reports/results.md-ийн хэсгүүдийг шинэчлэх туслах. Дахин ажиллуулахад хэсэг давхардахгүй."""
from __future__ import annotations

import re

from ml.common import REPORTS_DIR

RESULTS_PATH = REPORTS_DIR / "results.md"
ORDER = ["data", "classifier", "tracing", "recommender", "ocr", "summary"]
HEADER = "# Capstone II — ML үр дүн\n\nЭнэ файлыг скриптүүд автоматаар шинэчилнэ. Бүх тоо бодитоор ажиллуулсан үр дүн.\n"


def update_section(key: str, markdown: str) -> None:
    """`key` хэсгийг шинэ агуулгаар солино (байхгүй бол нэмнэ)."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    text = RESULTS_PATH.read_text(encoding="utf-8") if RESULTS_PATH.exists() else HEADER
    sections = dict(re.findall(r"<!-- BEGIN (\w+) -->\n(.*?)<!-- END \1 -->\n", text, flags=re.S))
    sections[key] = markdown.rstrip() + "\n"
    keys = [k for k in ORDER if k in sections] + [k for k in sections if k not in ORDER]
    body = "".join(f"<!-- BEGIN {k} -->\n{sections[k]}<!-- END {k} -->\n\n" for k in keys)
    RESULTS_PATH.write_text(HEADER + "\n" + body, encoding="utf-8")
