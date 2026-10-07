"""Хэлнээс хамаарахгүй, LaTeX/математикийн тэмдэгтэд суурилсан шинжүүд.

Монгол болон англи текстэд адилхан ажиллана: зөвхөн томьёоны тэмдэгт, командыг тоолно.
"""
from __future__ import annotations

import re

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

# (шинжийн нэр, regex). Юникод тэмдэгтийг (√, ², ≤, π ...) LaTeX командтай адил тооцно.
LATEX_PATTERNS: list[tuple[str, str]] = [
    ("frac", r"\\[dt]?frac|\d\s*/\s*\d"),
    ("sqrt", r"\\sqrt|√"),
    ("log", r"\\(log|lg|ln)\b|\blog|\bln\b"),
    ("trig", r"\\(sin|cos|tan|tg|cot|ctg|sec|csc)\b|\b(sin|cos|tg|ctg|tan)\b"),
    ("degree", r"\\circ|°"),
    ("greek", r"\\(alpha|beta|gamma|theta|pi|varphi)|[αβγθπφ]"),
    ("power", r"\^|[²³]"),
    ("var_square", r"[a-z]\s*(\^\s*\{?2\}?|²)"),
    ("var_exponent", r"\d\s*\^\s*\{?[^}]*[a-z]|[a-z]\s*\^\s*\{?[a-z]"),
    ("equals", r"="),
    ("inequality", r"[<>≤≥]|\\(le|ge|leq|geq|lt|gt)\b"),
    ("abs", r"\|"),
    ("function", r"\b[fgh]\s*\(|\by\s*="),
    ("point", r"[A-Z]\s*\(\s*-?\d+\s*[;,]"),
    ("combinatorics", r"\b[CPA]_|\\binom|\d\s*!|\bP\s*\("),
    ("cases", r"\\begin\{cases\}|\\\\"),
    ("cdot", r"\\cdot|\\times|·|×"),
    ("variable", r"(?<![a-zA-Z\\])[a-z](?![a-zA-Z])"),
    ("digit", r"\d+"),
]
_COMPILED = [(name, re.compile(p)) for name, p in LATEX_PATTERNS]
FEATURE_NAMES = [name for name, _ in LATEX_PATTERNS]


def latex_features(text: str) -> np.ndarray:
    """Нэг бодлогын шинжийн вектор: тэмдэгт тус бүрийн тоо (log1p)."""
    counts = [len(rx.findall(text or "")) for _, rx in _COMPILED]
    return np.log1p(np.asarray(counts, dtype=float))


class LatexFeatures(BaseEstimator, TransformerMixin):
    """sklearn pipeline-д оруулах трансформер."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return np.vstack([latex_features(x) for x in X])

    def get_feature_names_out(self, input_features=None):
        return np.array([f"latex_{n}" for n in FEATURE_NAMES])
