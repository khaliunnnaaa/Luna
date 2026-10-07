"""FR-10: Сурагчийн хариуг тоон болон алгебрийн эквивалент байдлаар шалгах."""

import re

from sympy import simplify
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

# sympify/parse_expr дотроо eval ашигладаг тул хэрэглэгчийн оролтыг заавал шүүнэ.
_ALLOWED = re.compile(r"^[0-9a-zA-Z+\-*/^().,\s]{1,200}$")
_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)


def _parse(expr: str):
    if not _ALLOWED.match(expr) or "__" in expr:
        raise ValueError("Зөвшөөрөгдөөгүй тэмдэгт")
    return parse_expr(expr.replace("^", "**"), transformations=_TRANSFORMS, evaluate=True)


def is_equivalent(student: str, correct: str) -> bool:
    """`1/2` ба `0.5`, `2(x+1)` ба `2x+2` гэх мэтийг тэнцүү гэж үзнэ."""
    try:
        diff = simplify(_parse(student) - _parse(correct))
    except Exception:  # noqa: BLE001 — буруу оролт = буруу хариу
        return False
    if diff == 0:
        return True
    return bool(diff.is_number) and abs(float(diff)) < 1e-9
