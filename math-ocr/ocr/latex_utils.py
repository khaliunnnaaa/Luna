"""LaTeX цэвэрлэх, хэвшүүлэх (normalize), шалгах туслах функцууд.

Үнэлгээнд (NFR-05) хоёр LaTeX-ийг харьцуулахдаа хоосон зай, \\mathrm, \\left/\\right зэрэг
утга өөрчлөхгүй ялгааг арилгаж байж тулгана.
"""
from __future__ import annotations

import re

_UNICODE_MAP = {
    "−": "-", "–": "-", "·": r"\cdot ", "×": r"\times ", "÷": r"\div ", "≤": r"\le ", "≥": r"\ge ",
    "≠": r"\ne ", "±": r"\pm ", "π": r"\pi ", "α": r"\alpha ", "β": r"\beta ", "∞": r"\infty ",
    "√": r"\sqrt ", "°": r"^{\circ}",
}
_SUP = {"²": "2", "³": "3", "¹": "1", "⁰": "0", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
# Монгол сурах бичгийн тэмдэглэгээ -> стандарт LaTeX
_FUNC_ALIASES = {r"\operatorname{tg}": r"\tan", r"\mathrm{tg}": r"\tan", r"\operatorname{ctg}": r"\cot",
                 r"\mathrm{ctg}": r"\cot", r"\operatorname{lg}": r"\lg", r"\mathrm{lg}": r"\lg",
                 r"\operatorname{log}": r"\log", r"\mathrm{log}": r"\log", r"\operatorname{arctg}": r"\arctan"}


def clean_latex(s: str) -> str:
    """Загварын гаралтыг харуулахад (KaTeX) бэлдэнэ."""
    s = s.strip().strip("$").strip()
    for a, b in _FUNC_ALIASES.items():
        s = s.replace(a, b)
    s = re.sub(r"\\(displaystyle|textstyle|scriptstyle)\s*", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def unicode_to_latex(s: str) -> str:
    """Tesseract-ын уншсан 'x² − 5x + 6 = 0' маягийн мөрийг ойролцоо LaTeX болгоно (fallback)."""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c in _SUP:
            j = i
            digits = ""
            while j < len(s) and s[j] in _SUP:
                digits += _SUP[s[j]]
                j += 1
            out.append("^{" + digits + "}")
            i = j
            continue
        out.append(_UNICODE_MAP.get(c, c))
        i += 1
    r = "".join(out)
    r = re.sub(r"(?<![\\a-z])log(\d+)", r"\\log_{\1}", r)         # log2 8 -> \log_{2} 8
    r = re.sub(r"(?<!\\)\b(ctg|tg)\b", lambda m: "cot" if m.group(1) == "ctg" else "tan", r)
    r = re.sub(r"(?<!\\)\b(sin|cos|tan|cot|log|lg|ln)\b", r"\\\1", r)
    # OCR дээд индексийг алдсан: x2 -> x^{2}. Харин дараалал/прогрессийн a1, b2, S5 бол доод индекс
    r = re.sub(r"(?<![\\a-zA-Z])([xyz])(\d)\b", r"\1^{\2}", r)
    r = re.sub(r"(?<![\\a-zA-Z])([a-wA-Z])(\d{1,2})\b", r"\1_{\2}", r)
    return re.sub(r"\s+", " ", r).strip()


def normalize_for_match(s: str) -> str:
    """Үнэлгээнд: утга нь ижил хоёр LaTeX-ийг ижил мөр болгох."""
    s = clean_latex(s)
    s = re.sub(r"\\(left|right|big|Big|bigg|Bigg)\b", "", s)
    s = re.sub(r"\\(mathrm|mathit|text|operatorname)\s*\{([^{}]*)\}", r"\2", s)
    s = s.replace(r"\,", "").replace(r"\;", "").replace(r"\!", "").replace(r"\ ", "").replace("~", "")
    s = s.replace(r"\dfrac", r"\frac").replace(r"\tfrac", r"\frac").replace(r"\leqslant", r"\le").replace(r"\geqslant", r"\ge")
    s = s.replace(r"\leq", r"\le").replace(r"\geq", r"\ge").replace(r"\neq", r"\ne")
    s = re.sub(r"\^\{(\w)\}", r"^\1", s)      # x^{2} == x^2
    s = re.sub(r"_\{(\w)\}", r"_\1", s)
    s = re.sub(r"\s+", "", s)
    return s


def tokenize(s: str) -> list[str]:
    return re.findall(r"\\[a-zA-Z]+|\\.|[^\s]", s)


def edit_distance(a: list, b: list) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def plausibility(s: str) -> float:
    """pix2tex итгэлцүүр өгдөггүй тул гаралтын 'эрүүл' байдлыг 0..1 оноогоор үнэлнэ.

    Хаалт тэнцвэргүй, давтагдсан гогцоо, хэт урт гаралт — алдаатай таних шинж.
    """
    if not s:
        return 0.0
    score = 1.0
    if s.count("{") != s.count("}"):
        score -= 0.5
    if s.count("(") != s.count(")") and r"\left" not in s:
        score -= 0.15
    toks = tokenize(s)
    if len(toks) > 8:
        # ижил 4-gram олон давтагдвал (загвар гацсан шинж)
        grams = [tuple(toks[i:i + 4]) for i in range(len(toks) - 3)]
        rep = 1 - len(set(grams)) / len(grams)
        score -= min(0.5, rep)
    if len(toks) > 250:
        score -= 0.3
    return max(0.0, round(score, 2))
