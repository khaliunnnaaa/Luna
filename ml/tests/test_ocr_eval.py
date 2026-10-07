from ml.ocr.evaluate import levenshtein, normalize_latex, normalized_edit_distance, score
from ml.ocr.pipeline import split_words


def test_normalize_latex():
    assert normalize_latex(r"\dfrac{1}{2} \, + \left( x \right)") == normalize_latex(r"\frac12+(x)")


def test_levenshtein():
    assert levenshtein("kitten", "sitting") == 3
    assert normalized_edit_distance("x^2", "x^2") == 0


def test_score():
    r = score(["x^2", "y"], ["x^{2}", "z"])
    assert r["exact_match"] == 0.5
    assert 0 < r["char_accuracy"] < 1


def test_split_words():
    words = [{"text": t, "line": 1, "left": 10 * i, "top": 0, "width": 8, "height": 10}
             for i, t in enumerate(["Тэгшитгэлийг", "бод.", "x^2", "-", "4=0"])]
    lines, regions = split_words(words)
    assert lines == ["Тэгшитгэлийг бод."]
    assert regions == [(20, 0, 48, 10)]
