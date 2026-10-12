"""Загваруудыг татаж суулгах (Windows / macOS / Linux).

    python -m tools.setup_models

1. Tesseract-ийн монгол хэлний загвар (tessdata_best/mon.traineddata) — tessdata хавтас руу
2. pix2tex-ийн анхны жин (эхний ачааллаар автоматаар татна)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request

TESS_URL = "https://github.com/tesseract-ocr/tessdata_best/raw/main/{lang}.traineddata"


def tessdata_dir() -> str:
    if os.getenv("TESSDATA_PREFIX"):
        return os.environ["TESSDATA_PREFIX"]
    exe = shutil.which("tesseract")
    if not exe:
        sys.exit("Tesseract олдсонгүй. Суулгах: Windows — https://github.com/UB-Mannheim/tesseract/wiki , "
                 "macOS — brew install tesseract , Ubuntu — sudo apt install tesseract-ocr")
    out = subprocess.run([exe, "--list-langs"], capture_output=True, text=True)
    line = (out.stdout + out.stderr).splitlines()[0]
    # 'List of available languages in "/usr/share/tesseract-ocr/5/tessdata/" (2):'
    if '"' in line:
        return line.split('"')[1]
    return os.path.join(os.path.dirname(exe), "tessdata")


def main() -> None:
    d = tessdata_dir()
    for lang in ("mon", "eng"):
        dst = os.path.join(d, f"{lang}.traineddata")
        if os.path.exists(dst) and os.path.getsize(dst) > 1_000_000:
            print(f"✓ {lang} байна: {dst}")
            continue
        print(f"↓ {lang}.traineddata татаж байна -> {dst}")
        try:
            urllib.request.urlretrieve(TESS_URL.format(lang=lang), dst)
        except PermissionError:
            local = os.path.abspath("tessdata")
            os.makedirs(local, exist_ok=True)
            urllib.request.urlretrieve(TESS_URL.format(lang=lang), os.path.join(local, f"{lang}.traineddata"))
            print(f"  Эрх хүрэлцээгүй тул {local} руу татлаа. TESSDATA_PREFIX={local} гэж тохируулна уу.")
    try:
        from pix2tex.cli import LatexOCR
        print("↓ pix2tex жин татаж/ачаалж байна...")
        LatexOCR()
        print("✓ pix2tex бэлэн")
    except ImportError:
        print("! pix2tex суулгаагүй: pip install 'pix2tex[api]'")


if __name__ == "__main__":
    main()
