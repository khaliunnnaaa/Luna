"""Текст ба томьёоны хэсгийг ялгах (layout шинжилгээ).

Монгол бодлогын зурагт нэг мөрөнд текст, томьёо холилдсон байдаг:
    "Тэгшитгэлийг бод: x² − 5x + 6 = 0"
Tesseract-аар бүх үгийг уншаад, монгол үг шиг харагдах, итгэлцүүр өндөр үгсийг ТЕКСТ,
үлдсэнийг ТОМЬЁО гэж ангилна. Дараа нь томьёоны үгсийг нэгтгэж, бутархай, зэрэг зэрэг
дээш доош сунасан хэсгийг connected-component-оор хамруулж тайрна.

Нэмэлтээр (заавал биш) YOLO төрлийн томьёо илрүүлэгч (MFD) ONNX загвар өгвөл
томьёоны байрлалыг тэр загвараар олно — холимог мөрөнд илүү нарийвчлалтай.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import cv2
import numpy as np

from .text_ocr import Word

CYR = "А-Яа-яЁёӨөҮү"
# Монгол үг: 2+ кирилл үсэг, зураастай нийлмэл үг, өмнө/ард нь цэг таслал байж болно
RE_MN_WORD = re.compile(rf"^[«\"“(]?[{CYR}]{{2,}}(?:-[{CYR}]+)*[.,:;!?»\"”)]*$")
# Дугаарлалт: "1.", "2)", "а)", "б."
RE_LABEL = re.compile(rf"^(?:\d{{1,2}}|[{CYR}a-z])[.)]$")
RE_NUMBER = re.compile(r"^[\d]+(?:[.,]\d+)?[.,:;]?$")
RE_PUNCT = re.compile(r"^(?:[.,:;!?«»\"“”]+|[—–-])$")
MATH_CHARS = set("=+−-—–_*/^√∑∫<>≤≥≠±·×÷()[]{}|²³¹⁰⁴⁵⁶⁷⁸⁹π") | {chr(c) for c in range(0x3B1, 0x3CA)}
MATH_WORDS = {"sin", "cos", "tg", "tan", "ctg", "cot", "log", "lg", "ln", "lim", "arcsin",
              "arccos", "arctg", "max", "min", "exp"}

TEXT_CONF = 55.0


@dataclass
class Region:
    kind: str                     # "text" | "formula"
    x: int
    y: int
    x2: int
    y2: int
    words: list[Word] = field(default_factory=list)
    content: str = ""             # текст эсвэл LaTeX
    conf: float = 0.0             # 0..1
    needs_review: bool = False

    @property
    def cy(self) -> float:
        return (self.y + self.y2) / 2

    @property
    def h(self) -> int:
        return self.y2 - self.y

    def box(self) -> list[int]:
        return [self.x, self.y, self.x2, self.y2]


def classify_word(w: Word, line_start: bool) -> str:
    """'text' | 'math' | 'neutral' (тоо, цэг таслал — хөршөөсөө хамаарна)."""
    t = w.text
    if line_start and RE_LABEL.match(t):
        return "text"
    low = t.lower().strip(".,:;")
    if low in MATH_WORDS or any(low.startswith(m) for m in ("log", "sin", "cos", "lg", "ln", "tg", "ctg", "lim")):
        return "math"     # log5 -> "logs" гэж уншсан ч томьёо
    if RE_PUNCT.match(t):
        return "neutral"
    if RE_NUMBER.match(t):
        return "neutral"
    if RE_MN_WORD.match(t) and w.conf >= TEXT_CONF:
        return "text"
    if any(c in MATH_CHARS for c in t):
        return "math"
    # Нэг үсэг (x, y, a ...), латин үсэг, итгэлцүүр бага — томьёо
    return "math"


def _group_lines(words: list[Word]) -> list[list[Word]]:
    lines: dict[tuple, list[Word]] = {}
    for w in words:
        lines.setdefault(w.line_id, []).append(w)
    out = [sorted(ws, key=lambda w: w.x) for ws in lines.values()]
    out.sort(key=lambda ws: np.median([w.y + w.h / 2 for w in ws]))
    return out


def _resolve_neutral(labels: list[str]) -> list[str]:
    """Тоо, цэг таслалыг хөршийнх нь ангиллаар солино."""
    out = labels[:]
    n = len(out)
    for i, l in enumerate(out):
        if l != "neutral":
            continue
        left = next((out[j] for j in range(i - 1, -1, -1) if out[j] != "neutral"), None)
        right = next((labels[j] for j in range(i + 1, n) if labels[j] != "neutral"), None)
        out[i] = "math" if "math" in (left, right) else "text"
    # Мөрийн төгсгөлийн цэг таслал томьёонд орох ёсгүй
    return out


def _cc_boxes(binary: np.ndarray) -> np.ndarray:
    inv = 255 - binary
    n, _, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=8)
    st = stats[1:]
    keep = st[:, cv2.CC_STAT_AREA] >= 6           # жижиг толбыг хаяна
    st = st[keep]
    return np.stack([st[:, 0], st[:, 1], st[:, 0] + st[:, 2], st[:, 1] + st[:, 3]], axis=1) if len(st) else np.zeros((0, 4), int)


def find_fraction_zones(cc: np.ndarray, line_h: float) -> list[list[int]]:
    """Бутархайн зураасыг (нимгэн урт хэвтээ шугам, дээр доор нь бэх бүхий) олж,
    хүртвэр+зураас+хуваарийг хамарсан хүрээ буцаана.

    Tesseract бутархайг 2-3 тусдаа мөр гэж уншдаг тул үгийн ангиллаас өмнө бүтцээр нь илрүүлнэ.
    """
    zones = []
    if len(cc) == 0:
        return zones
    w = cc[:, 2] - cc[:, 0]
    h = cc[:, 3] - cc[:, 1]
    bars = np.where((w >= 0.45 * line_h) & (h <= max(4, 0.22 * line_h)) & (w >= 4 * h))[0]
    for b in bars:
        x1, y1, x2, y2 = cc[b]
        ov = (np.minimum(cc[:, 2], x2) - np.maximum(cc[:, 0], x1)) > 0.3 * np.minimum(w, x2 - x1).clip(1)
        # Хүртвэр/хуваарь зураастай ойрхон (≤0.6 мөрийн өндөр) байна; хасах тэмдэг ба
        # өмнөх/дараах мөрийн үсгийг андуурахгүйн тулд зай болон хэмжээг хязгаарлана
        small = (cc[:, 3] - cc[:, 1]) <= 1.6 * line_h
        cx = (cc[:, 0] + cc[:, 2]) / 2
        centered = (cx >= x1 - 2) & (cx <= x2 + 2)          # хүртвэр/хуваарь зураасын дээр/доор төвлөрсөн
        above = ov & small & centered & (cc[:, 3] <= y1 + 1) & (cc[:, 3] >= y1 - 0.9 * line_h)
        below = ov & small & centered & (cc[:, 1] >= y2 - 1) & (cc[:, 1] <= y2 + 0.9 * line_h)
        above[b] = below[b] = False
        if above.any() and below.any():
            grp = cc[above | below]
            zones.append([int(min(x1, grp[:, 0].min())), int(grp[:, 1].min()),
                          int(max(x2, grp[:, 2].max())), int(grp[:, 3].max())])
    return zones


def _expand_formula(r: Region, cc: np.ndarray, text_boxes: list[tuple], line_h: float) -> None:
    """Бутархайн хүртвэр/хуваарь, зэрэг, язгуурын тэмдгийг хамруулахаар томьёоны хүрээг тэлнэ."""
    for _ in range(3):
        changed = False
        ymin, ymax = r.y - 1.2 * line_h, r.y2 + 1.2 * line_h
        for x1, y1, x2, y2 in cc:
            if x2 < r.x - 2 or x1 > r.x2 + 2 or y2 < ymin or y1 > ymax:
                continue
            if x1 >= r.x - 2 and x2 <= r.x2 + 2 and y1 >= r.y and y2 <= r.y2:
                continue
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            if any(tx1 <= cx <= tx2 and ty1 <= cy <= ty2 for tx1, ty1, tx2, ty2 in text_boxes):
                continue
            # Бутархайн зураас мэт урт хэвтээ шугам эсвэл хүрээтэй давхцсан зүйл
            if (x2 - x1) > 3 * line_h and (y2 - y1) > 2 * line_h:
                continue  # хүснэгтийн хүрээ, зураг — алгасна
            nx, ny, nx2, ny2 = min(r.x, x1), min(r.y, y1), max(r.x2, x2), max(r.y2, y2)
            if (nx, ny, nx2, ny2) != (r.x, r.y, r.x2, r.y2):
                r.x, r.y, r.x2, r.y2 = nx, ny, nx2, ny2
                changed = True
        if not changed:
            break


def _overlap(a: Region, b: Region, pad: int = 2, padx: float = 2) -> bool:
    return not (a.x2 + padx < b.x or b.x2 + padx < a.x or a.y2 + pad < b.y or b.y2 + pad < a.y)


def _merge_overlapping(regs: list[Region], padx: float = 2) -> list[Region]:
    """Давхацсан эсвэл хэвтээ чиглэлд ойрхон (padx) томьёонуудыг нэг болгоно."""
    regs = regs[:]
    merged = True
    while merged:
        merged = False
        for i in range(len(regs)):
            for j in range(i + 1, len(regs)):
                a, b = regs[i], regs[j]
                if _overlap(a, b, padx=padx):
                    a.x, a.y, a.x2, a.y2 = min(a.x, b.x), min(a.y, b.y), max(a.x2, b.x2), max(a.y2, b.y2)
                    a.words += b.words
                    regs.pop(j)
                    merged = True
                    break
            if merged:
                break
    return regs


def segment(words: list[Word], binary: np.ndarray, mfd_boxes: list[list[int]] | None = None) -> list[Region]:
    """Үгсийг текст ба томьёоны бүсүүд болгон хуваана."""
    if not words:
        return []
    heights = [w.h for w in words if w.h > 0]
    line_h = float(np.median(heights)) if heights else 20.0

    if mfd_boxes:
        return _segment_with_detector(words, mfd_boxes)

    cc = _cc_boxes(binary)
    zones = find_fraction_zones(cc, line_h)

    def in_zone(w: Word) -> bool:
        cx, cy = w.x + w.w / 2, w.y + w.h / 2
        return any(z[0] <= cx <= z[2] and z[1] <= cy <= z[3] for z in zones)

    text_regs: list[Region] = []
    math_regs: list[Region] = [Region("formula", *z) for z in zones]
    for ws in _group_lines(words):
        labels = [("math" if in_zone(w) else classify_word(w, i == 0)) for i, w in enumerate(ws)]
        labels = _resolve_neutral(labels)
        cur: Region | None = None
        for w, lab in zip(ws, labels):
            kind = "formula" if lab == "math" else "text"
            gap_ok = cur is not None and (w.x - cur.x2) < 2.5 * line_h
            if cur is not None and cur.kind == kind and gap_ok:
                cur.x2, cur.y, cur.y2 = max(cur.x2, w.x2), min(cur.y, w.y), max(cur.y2, w.y2)
                cur.words.append(w)
            else:
                cur = Region(kind, w.x, w.y, w.x2, w.y2, [w])
                (math_regs if kind == "formula" else text_regs).append(cur)

    # Мөрийн төгсгөлийн цэг таслалыг томьёоноос салгах
    for r in math_regs:
        while len(r.words) > 1 and RE_PUNCT.match(r.words[-1].text):
            p = r.words.pop()
            r.x2 = max(w.x2 for w in r.words)
            text_regs.append(Region("text", p.x, p.y, p.x2, p.y2, [p]))

    text_boxes = [(w.x, w.y, w.x2, w.y2) for r in text_regs for w in r.words]
    for r in math_regs:
        _expand_formula(r, cc, text_boxes, line_h)
    math_regs = _merge_overlapping(math_regs, padx=0.8 * line_h)

    # Томьёонд залгигдсан текстийн үгсийг (жишээ нь бутархайн хүртвэр дээрх) хасна
    def inside(t: Region, f: Region) -> bool:
        cx, cy = (t.x + t.x2) / 2, t.cy
        return f.x <= cx <= f.x2 and f.y <= cy <= f.y2
    text_regs = [t for t in text_regs if not any(inside(t, f) for f in math_regs)]

    # Шуугиан: үсэг/тоогүй, жижиг "томьёо" (; _ . гэх мэт) -> хаяна
    def junk(f: Region) -> bool:
        has_alnum = any(any(ch.isalnum() for ch in w.text) for w in f.words)
        small = (f.x2 - f.x) < 1.2 * line_h and f.h < 1.6 * line_h
        flat = f.h < 0.45 * line_h and not any(z[0] <= f.x and f.x2 <= z[2] for z in zones)
        return (small and not has_alnum) or flat
    math_regs = [f for f in math_regs if not junk(f)]
    return text_regs + math_regs


def _segment_with_detector(words: list[Word], boxes: list[list[int]]) -> list[Region]:
    formulas = [Region("formula", *map(int, b)) for b in boxes]
    texts: list[Region] = []
    for w in words:
        cx, cy = w.x + w.w / 2, w.y + w.h / 2
        if any(f.x <= cx <= f.x2 and f.y <= cy <= f.y2 for f in formulas):
            continue
        texts.append(Region("text", w.x, w.y, w.x2, w.y2, [w]))
    return texts + formulas


def order_into_lines(regs: list[Region]) -> list[list[Region]]:
    """Бүсүүдийг уншигдах дарааллаар (дээрээс доош, зүүнээс баруун) мөр болгон эрэмбэлнэ."""
    if not regs:
        return []
    med_h = float(np.median([max(r.h, 1) for r in regs if r.kind == "text"] or [20]))
    regs = sorted(regs, key=lambda r: r.cy)
    lines: list[list[Region]] = []
    for r in regs:
        if lines:
            last = lines[-1]
            ly = np.mean([q.cy for q in last])
            if abs(r.cy - ly) < 0.6 * max(med_h, min(r.h, 3 * med_h) / 2):
                last.append(r)
                continue
        lines.append([r])
    return [sorted(l, key=lambda r: r.x) for l in lines]


class MFDDetector:
    """Заавал биш: YOLOv8 форматын томьёо илрүүлэгч ONNX (жишээ нь Pix2Text-ийн MFD).

    Гаралт (1, 4+nc, N) хэлбэртэй стандарт YOLOv8 export гэж үзнэ.
    """

    def __init__(self, onnx_path: str, conf: float = 0.25, iou: float = 0.45, size: int = 768):
        import onnxruntime as ort
        self.sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name
        self.conf, self.iou, self.size = conf, iou, size

    def __call__(self, gray: np.ndarray) -> list[list[int]]:
        h, w = gray.shape[:2]
        s = self.size / max(h, w)
        nh, nw = int(h * s), int(w * s)
        canvas = np.full((self.size, self.size, 3), 114, np.uint8)
        canvas[:nh, :nw] = cv2.cvtColor(cv2.resize(gray, (nw, nh)), cv2.COLOR_GRAY2BGR)
        x = canvas[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        out = self.sess.run(None, {self.inp: x})[0][0]          # (4+nc, N)
        out = out.T
        scores = out[:, 4:].max(1)
        keep = scores > self.conf
        if not keep.any():
            return []
        b, sc = out[keep, :4], scores[keep]
        xyxy = np.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2, b[:, 0] + b[:, 2] / 2, b[:, 1] + b[:, 3] / 2], 1) / s
        idx = cv2.dnn.NMSBoxes([[float(a), float(c), float(e - a), float(f - c)] for a, c, e, f in xyxy],
                               sc.tolist(), self.conf, self.iou)
        idx = np.array(idx).flatten()
        return [[int(max(0, v)) for v in xyxy[i]] for i in idx]
