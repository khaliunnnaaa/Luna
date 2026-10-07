"""FR-10: Сурагчийн хариуг тоон болон алгебрийн эквивалент байдлаар шалгах.

Дэмжих хариуны хэлбэрүүд (бодлогын сангийн `хариу_sympy` баганатай ижил):
  - Илэрхийлэл:      1/2, 2*sqrt(2), (x - 3)*(x + 3)
  - Шийдүүдийн жагсаалт (дараалал хамаагүй): [3, 4], [pi/6, 5*pi/6]
  - Цэг / хос:        (2, -3)
  - Систем:           {x: 7, y: 3}
  - Завсар:           Interval(2, oo), Interval.open(-1, 5), Union(...)
"""

import re

from sympy import Basic, Set, simplify
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

# parse_expr нь дотроо eval ашигладаг тул: (1) оролтыг тэмдэгтээр шүүнэ,
# (2) Python-ий builtins (open, exec г.м.)-ийг хаана — зөвхөн SymPy-ийн нэрс үлдэнэ.
_ALLOWED = re.compile(r"^[0-9a-zA-Z+\-*/^().,\s\[\]{}:]{1,300}$")
_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)
_GLOBALS: dict = {}
exec("from sympy import *", _GLOBALS)  # noqa: S102 — тогтмол мөр, хэрэглэгчийн оролт биш
_GLOBALS["__builtins__"] = {}


def _parse(expr: str):
    if not _ALLOWED.match(expr) or "__" in expr:
        raise ValueError("Зөвшөөрөгдөөгүй тэмдэгт")
    return parse_expr(
        expr.replace("^", "**"),
        global_dict=dict(_GLOBALS),
        transformations=_TRANSFORMS,
        evaluate=True,
    )


def can_parse(expr: str) -> bool:
    """Админ хариу оруулахад SymPy уншиж чадах эсэхийг шалгана."""
    try:
        _parse(expr)
        return True
    except Exception:  # noqa: BLE001
        return False


def _equal(a, b) -> bool:
    """Хоёр уншсан хариуг харьцуулна (төрлөөс хамаарч)."""
    if isinstance(a, dict) or isinstance(b, dict):
        if not (isinstance(a, dict) and isinstance(b, dict)):
            return False
        ka, kb = {str(k): v for k, v in a.items()}, {str(k): v for k, v in b.items()}
        return ka.keys() == kb.keys() and all(_equal(ka[k], kb[k]) for k in ka)

    if isinstance(a, list) or isinstance(b, list):
        # Шийдүүдийн жагсаалт: дараалал хамаагүй. Ганц шийд бол [3] == 3 гэж үзнэ.
        la = a if isinstance(a, list) else [a]
        lb = b if isinstance(b, list) else [b]
        if len(la) != len(lb):
            return False
        rest = list(lb)
        for x in la:
            match = next((i for i, y in enumerate(rest) if _equal(x, y)), None)
            if match is None:
                return False
            rest.pop(match)
        return True

    if isinstance(a, tuple) or isinstance(b, tuple):
        # Цэг/хос: дараалал чухал
        if not (isinstance(a, tuple) and isinstance(b, tuple)) or len(a) != len(b):
            return False
        return all(_equal(x, y) for x, y in zip(a, b))

    if isinstance(a, Set) or isinstance(b, Set):
        return isinstance(a, Set) and isinstance(b, Set) and bool(a == b)

    if isinstance(a, Basic) and isinstance(b, Basic) or isinstance(a, (int, float)):
        diff = simplify(a - b)
        if diff == 0:
            return True
        return bool(diff.is_number) and abs(float(diff)) < 1e-9
    return False


def is_equivalent(student: str, correct: str) -> bool:
    """`1/2` ба `0.5`, `2(x+1)` ба `2x+2`, `[4, 3]` ба `[3, 4]` гэх мэтийг тэнцүү гэж үзнэ."""
    try:
        return _equal(_parse(student), _parse(correct))
    except Exception:  # noqa: BLE001 — буруу оролт = буруу хариу
        return False
