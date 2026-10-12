"""Монгол текстийн OCR алдаа засах.

Tesseract кирилл үгийн дунд латин ижил хэлбэртэй үсэг (a/а, o/о, e/е, p/р, c/с, x/х, y/у)
холих, ө/о, ү/у-г андуурах нь элбэг. Математикийн нэр томьёоны толиор ойролцоо үгийг засна.
"""
from __future__ import annotations

import re

LAT2CYR = str.maketrans({
    "a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х", "y": "у", "k": "к", "m": "м",
    "A": "А", "B": "В", "E": "Е", "H": "Н", "K": "К", "M": "М", "O": "О", "P": "Р", "C": "С",
    "T": "Т", "X": "Х", "Y": "У",
})
CYR = re.compile(r"[А-Яа-яЁёӨөҮү]")
LAT = re.compile(r"[A-Za-z]")

# Бодлогын өгүүлбэрт түгээмэл гардаг үгс. Админ нэр томьёоны толиос (FR-16) өргөтгөж болно.
MATH_TERMS = """
тэгшитгэл тэгшитгэлийг тэгшитгэлийн тэнцэтгэл тэнцэтгэлийг бод бодно ол олно олох шийд шийдийг
шийдийн утга утгыг утгын функц функцийн функцийг график графикийг хувьсагч илэрхийлэл илэрхийллийг
хялбарчил тооцоол тоо тооны бутархай бутархайг язгуур квадрат квадрат логарифм логарифмын
тригонометр өнцөг өнцгийн гурвалжин тойрог радиус диаметр талбай талбайг периметр эзлэхүүн
магадлал магадлалыг дараалал прогресс арифметик геометр гишүүн гишүүний нийлбэр үржвэр
ялгавар харьцаа хувь бүхэл натурал рациональ бодит тэнцүү их бага биш хэрэв бол тэгвэл
өгөгдсөн өгөгдөв дараах хэд хэдэн хэдэд хамгийн муж мужийг тодорхойлогдох уламжлал интеграл
хязгаар тэгш хэм цэг цэгийн координат шулуун хэрчим вектор матриц систем системийг
""".split()


def fix_homoglyphs(word: str) -> str:
    """Кирилл давамгай үгийн доторх латин үсгийг кирилл болгоно."""
    if CYR.search(word) and LAT.search(word):
        n_cyr = len(CYR.findall(word))
        n_lat = len(LAT.findall(word))
        if n_cyr >= n_lat:
            return word.translate(LAT2CYR)
    return word


def _lev1(a: str, b: str) -> bool:
    """Хоёр үг 1-ээс ихгүй засвараар ялгаатай эсэх."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    s, l = (a, b) if len(a) < len(b) else (b, a)
    return any(l[:i] + l[i + 1:] == s for i in range(len(l)))


_TERMS = set(MATH_TERMS)


def fix_terms(word: str) -> str:
    """о↔ө, у↔ү андуурлыг толиор засна."""
    core = word.strip(".,:;!?«»\"()")
    low = core.lower()
    if len(low) < 4 or low in _TERMS:
        return word
    for t in _TERMS:
        if len(t) == len(low) and _lev1(low, t):
            diff = [(x, y) for x, y in zip(low, t) if x != y]
            if diff and diff[0] in {("о", "ө"), ("у", "ү"), ("ө", "о"), ("ү", "у"), ("е", "э"), ("и", "й")}:
                fixed = t if core[0].islower() else t.capitalize()
                return word.replace(core, fixed)
    return word


def postprocess_text(text: str) -> str:
    return " ".join(fix_terms(fix_homoglyphs(w)) for w in text.split())
