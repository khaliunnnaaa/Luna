"""Синтетик бодлогын зураг үүсгэгч: (зураг, текст, LaTeX, томьёоны bbox) хос.

Хэрэглээ:
  1) pix2tex-ийг монгол сурах бичгийн фонт/хэв маягт fine-tune хийх нэмэлт өгөгдөл
     (өөрсдийн авсан ≥300 бодит зургийг нөхөж, 2-5 мянга болгох)
  2) layout ангилагчийг (текст/томьёо ялгах) туршиж, үнэлэх

    python -m tools.synth --out data/synth --n 2000

Гаралт:
    data/synth/images/000001.png        бүтэн бодлогын зураг
    data/synth/crops/0000000.png        томьёоны тайрмал; нэр = pix2tex_math.txt-ийн мөрийн дугаар
    data/synth/labels.jsonl             {"image", "text", "formulas":[{"latex","bbox"}], "markdown"}
    data/synth/pix2tex_math.txt         crops-ын LaTeX (pix2tex dataset формат: мөр бүр нэг томьёо)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONTS = [f for f in [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "C:/Windows/Fonts/times.ttf", "C:/Windows/Fonts/arial.ttf",
    "/Library/Fonts/Times New Roman.ttf", "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
] if os.path.exists(f)]

# Сэдэв тус бүрийн загвар (FR-04 сэдвүүдтэй уялдана)
TEMPLATES = [
    ("Тэгшитгэлийг бод:", lambda r: f"x^2 {r.choice('+-')} {r.randint(2, 9)}x {r.choice('+-')} {r.randint(1, 20)} = 0"),
    ("Тэнцэтгэл бишийг бод:", lambda r: f"{r.randint(2, 7)}x - {r.randint(1, 9)} > {r.randint(1, 15)}"),
    ("Илэрхийллийг хялбарчил:", lambda r: rf"\frac{{x^2 - {r.randint(1, 9) ** 2}}}{{x + {r.randint(1, 9)}}}"),
    ("Утгыг ол:", lambda r: rf"\log_{{{r.choice([2, 3, 5])}}} {r.choice([8, 9, 25, 27, 32, 81])}"),
    ("Тооцоол:", lambda r: rf"\sqrt{{{r.randint(2, 99)}}} + \sqrt{{{r.randint(2, 99)}}}"),
    ("Функцийн тодорхойлогдох мужийг ол:", lambda r: rf"y = \sqrt{{{r.randint(1, 9)} - x}}"),
    ("Тэгшитгэлийг бод:", lambda r: rf"\sin x = \frac{{{r.choice([1, 1])}}}{{{r.choice([2, 2])}}}"),
    ("Хэрэв", lambda r: rf"a_1 = {r.randint(1, 9)},\ d = {r.randint(2, 5)}"),
    ("Тэгшитгэлийг бод:", lambda r: rf"{r.choice([2, 3, 5])}^{{x+{r.randint(1, 3)}}} = {r.choice([8, 9, 25, 27, 125])}"),
    ("Магадлалыг ол:", lambda r: rf"P(A) = \frac{{{r.randint(1, 5)}}}{{{r.randint(6, 12)}}}"),
]


def render_math(latex: str, fontsize: float, dpi: int = 200, fontset: str = "cm") -> np.ndarray:
    """matplotlib mathtext-ээр LaTeX-ийг саарал зураг болгоно (LaTeX суулгах шаардлагагүй)."""
    plt.rcParams["mathtext.fontset"] = fontset
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${latex}$", fontsize=fontsize)
    buf = io.BytesIO()
    fig.savefig(buf, dpi=dpi, transparent=False, bbox_inches="tight", pad_inches=0.02, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    a = np.array(Image.open(buf).convert("L"))
    ys, xs = np.where(a < 200)                     # бэхний хүрээгээр нарийн тайрна (GT bbox нарийвчлалтай)
    if len(xs):
        a = a[max(0, ys.min() - 2): ys.max() + 3, max(0, xs.min() - 2): xs.max() + 3]
    return a


def to_target_latex(s: str) -> str:
    """mathtext-д зориулсан бичлэгийг сургалтын шошго болгох (\\ зайг хасна)."""
    return s.replace(r"\ ", " ").strip()


def make_sample(r: random.Random) -> tuple[np.ndarray, dict]:
    prefix, gen = r.choice(TEMPLATES)
    latex = gen(r)
    suffix = " бол арифметик прогрессийн 10-р гишүүнийг ол." if prefix == "Хэрэв" else ""
    font_path = r.choice(FONTS)
    size = r.randint(26, 40)
    font = ImageFont.truetype(font_path, size)

    # size px өндөр тексттэй ойролцоо: pt = px * 72 / dpi
    # Сурах бичигт бутархайг ихэвчлэн том (display) хэлбэрээр бичдэг
    math = render_math(latex.replace(r"\frac", r"\dfrac"), fontsize=size * 72 / 200 * r.uniform(0.95, 1.15),
                       fontset=r.choice(["cm", "stix", "dejavuserif"]))
    # Текстийн өндөртэй тааруулна
    W = 60 + int(font.getlength(prefix)) + math.shape[1] + int(font.getlength(suffix)) + 80
    H = max(math.shape[0], size) + 80
    canvas = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(canvas)
    x, base = 40, H // 2
    d.text((x, base), prefix, font=font, fill=0, anchor="lm")
    x += int(font.getlength(prefix)) + int(size * 0.4)
    my = base - math.shape[0] // 2
    canvas.paste(Image.fromarray(math), (x, my))
    fbox = [x, my, x + math.shape[1], my + math.shape[0]]
    x += math.shape[1] + int(size * 0.2)
    if suffix:
        d.text((x, base), suffix.strip(), font=font, fill=0, anchor="lm")

    img = np.array(canvas)
    img = augment(img, r)
    label = {"text": f"{prefix}{suffix}", "formulas": [{"latex": to_target_latex(latex), "bbox": fbox}],
             "markdown": f"{prefix} ${to_target_latex(latex)}$" + (f" {suffix.strip()}" if suffix else "")}
    return img, label


def augment(img: np.ndarray, r: random.Random) -> np.ndarray:
    """Утасны камерын нөхцөлийг дуурайх: бага зэрэг эргүүлэх, бүдгэрүүлэх, шуугиан, сүүдэр."""
    h, w = img.shape
    if r.random() < 0.6:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), r.uniform(-3, 3), 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderValue=255)
    if r.random() < 0.4:
        img = cv2.GaussianBlur(img, (3, 3), r.uniform(0.3, 1.0))
    if r.random() < 0.5:
        grad = np.linspace(r.uniform(0.75, 1), 1, w)[None, :]
        img = (img.astype(np.float32) * grad).clip(0, 255).astype(np.uint8)
    if r.random() < 0.5:
        img = (img.astype(np.int16) + np.random.default_rng(r.randint(0, 1 << 30)).normal(0, 8, img.shape)).clip(0, 255).astype(np.uint8)
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/synth")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    r = random.Random(a.seed)
    os.makedirs(f"{a.out}/images", exist_ok=True)
    os.makedirs(f"{a.out}/crops", exist_ok=True)
    with open(f"{a.out}/labels.jsonl", "w", encoding="utf-8") as lf, \
            open(f"{a.out}/pix2tex_math.txt", "w", encoding="utf-8") as mf:
        c = 0  # pix2tex: crops/{мөрийн дугаар}.png <-> pix2tex_math.txt-ийн мөр
        for i in range(a.n):
            img, lab = make_sample(r)
            name = f"{i:06d}.png"
            cv2.imwrite(f"{a.out}/images/{name}", img)
            for k, f in enumerate(lab["formulas"]):
                x1, y1, x2, y2 = f["bbox"]
                cv2.imwrite(f"{a.out}/crops/{c:07d}.png", img[max(0, y1 - 4):y2 + 4, max(0, x1 - 4):x2 + 4])
                mf.write(f["latex"] + "\n")
                c += 1
            lf.write(json.dumps({"image": f"images/{name}", **lab}, ensure_ascii=False) + "\n")
    print(f"{a.n} зураг -> {a.out}")


if __name__ == "__main__":
    main()
