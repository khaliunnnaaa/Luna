import pytest

from app.services.answer_checker import is_equivalent

EQUIVALENT = [
    ("1/2", "0.5"),
    ("2*(x+1)", "2*x+2"),
    ("2(x+1)", "2x+2"),
    ("x^2", "x**2"),
    ("sqrt(4)", "2"),
    ("x**2-1", "(x-1)*(x+1)"),
]

NOT_EQUIVALENT = [
    ("1/3", "0.5"),
    ("x+1", "x-1"),
    ("abc((", "1"),
    ("__import__(1)", "1"),
]


@pytest.mark.parametrize("student,correct", EQUIVALENT)
def test_equivalent(student, correct):
    assert is_equivalent(student, correct)


@pytest.mark.parametrize("student,correct", NOT_EQUIVALENT)
def test_not_equivalent(student, correct):
    assert not is_equivalent(student, correct)
