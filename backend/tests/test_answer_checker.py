import pytest

from app.services.answer_checker import can_parse, is_equivalent

EQUIVALENT = [
    ("1/2", "0.5"),
    ("2*(x+1)", "2*x+2"),
    ("2(x+1)", "2x+2"),
    ("x^2", "x**2"),
    ("sqrt(4)", "2"),
    ("x**2-1", "(x-1)*(x+1)"),
    # Бодлогын сангийн хэлбэрүүд
    ("[4, 3]", "[3, 4]"),  # шийдүүдийн дараалал хамаагүй
    ("3", "[3]"),  # ганц шийд
    ("[1+sqrt(2), 1-sqrt(2)]", "[1 - sqrt(2), 1 + sqrt(2)]"),
    ("[pi/6, 5pi/6]", "[pi/6, 5*pi/6]"),
    ("(2, -3)", "(2, -3)"),
    ("{y: 3, x: 7}", "{x: 7, y: 3}"),
    ("Interval(2, oo)", "Interval(2, oo)"),
]

NOT_EQUIVALENT = [
    ("1/3", "0.5"),
    ("x+1", "x-1"),
    ("abc((", "1"),
    ("[3, 5]", "[3, 4]"),
    ("[3]", "[3, 4]"),
    ("(-3, 2)", "(2, -3)"),  # цэгийн координатын дараалал чухал
    ("{x: 7, y: 4}", "{x: 7, y: 3}"),
    ("Interval.open(2, oo)", "Interval(2, oo)"),
]

# Аюулгүй байдал: Python-ий builtins (open, exec, eval) ажиллах ёсгүй.
# Эдгээр нь SymPy-ийн энгийн тэмдэгт (функцийн нэр) болж уншигдана, код ажиллахгүй.
DANGEROUS = ["open(1)", "exec(1)", "eval(1)"]


@pytest.mark.parametrize("student,correct", EQUIVALENT)
def test_equivalent(student, correct):
    assert is_equivalent(student, correct)


@pytest.mark.parametrize("student,correct", NOT_EQUIVALENT)
def test_not_equivalent(student, correct):
    assert not is_equivalent(student, correct)


@pytest.mark.parametrize("expr", DANGEROUS)
def test_builtins_not_executed(expr):
    from sympy import Basic

    from app.services.answer_checker import _parse

    assert isinstance(_parse(expr), Basic)  # файл нээгдэхгүй, код ажиллахгүй
    assert not is_equivalent(expr, "1")


def test_dunder_blocked():
    assert not can_parse("__import__(1)")
    assert not can_parse("x.__class__")
