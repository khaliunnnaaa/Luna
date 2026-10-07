#!/usr/bin/env python3
"""
Capstone II — dataset_catalog.xlsx-ийн "Автомат" гэж тэмдэглэсэн өгөгдлийг татах скрипт.

Хэрэглээ:
    python download_datasets.py --list                 # татах боломжтой зүйлсийг харах
    python download_datasets.py                        # бүгдийг татах (im2latex зураггүй)
    python download_datasets.py --images               # im2latex-ийн томьёоны зургийг бас татах (том файл)
    python download_datasets.py --only math gsm8k      # заасан зүйлсийг л татах
    python download_datasets.py --out D:/capstone/data # хадгалах хавтас солих

Шаардлага:
    pip install datasets
    git (MM-Eval-ийг clone хийхэд)
"""
import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

# MATH: geometry, number_theory нь цар хүрээнээс гадуур тул татахгүй (каталогийн тэмдэглэл)
MATH_KEEP = [
    "algebra",
    "counting_and_probability",
    "intermediate_algebra",
    "prealgebra",
    "precalculus",
]

IM2LATEX_BASE = "https://zenodo.org/records/56198/files/"
IM2LATEX_LISTS = [
    "im2latex_formulas.lst",
    "im2latex_train.lst",
    "im2latex_validate.lst",
    "im2latex_test.lst",
]
IM2LATEX_IMAGES = "formula_images.tar.gz"

TESS_MON_URL = "https://github.com/tesseract-ocr/tessdata_best/raw/main/mon.traineddata"
ASSIST09_PYBKT_URL = "https://raw.githubusercontent.com/CAHLR/pyBKT-examples/master/data/as.csv"
MMEVAL_REPO = "https://github.com/joenahm/MM-Eval.git"


# ---------------------------------------------------------------- туслах функцууд
def download(url: str, dest: Path) -> None:
    """URL-аас файл татна. Аль хэдийн байвал алгасна."""
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  = байна, алгаслаа: {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    print(f"  ↓ {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "capstone-ii-downloader"})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)
    tmp.replace(dest)
    print(f"  ✓ {dest} ({dest.stat().st_size / 1e6:.1f} MB)")


def write_jsonl(rows, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def need_datasets():
    try:
        from datasets import load_dataset  # noqa: F401
    except ImportError:
        sys.exit("`datasets` сан алга. Эхлээд: pip install datasets")


# ---------------------------------------------------------------- dataset бүр
def get_math(out: Path, args) -> None:
    need_datasets()
    from datasets import load_dataset
    d = out / "math_hendrycks"
    for subj in MATH_KEEP:
        ds = load_dataset("EleutherAI/hendrycks_math", subj)
        for split in ds:
            n = write_jsonl(ds[split], d / f"{subj}_{split}.jsonl")
            print(f"  ✓ {subj}/{split}: {n} бодлого")


def get_gsm8k(out: Path, args) -> None:
    need_datasets()
    from datasets import load_dataset
    ds = load_dataset("openai/gsm8k", "main")
    for split in ds:
        n = write_jsonl(ds[split], out / "gsm8k" / f"{split}.jsonl")
        print(f"  ✓ gsm8k/{split}: {n} бодлого")


def get_mmeval(out: Path, args) -> None:
    dest = out / "mm_eval"
    if dest.exists():
        print(f"  = байна, алгаслаа: {dest}")
        return
    if shutil.which("git") is None:
        raise RuntimeError("git суугаагүй байна. git суулгах эсвэл GitHub-аас ZIP-ээр гараар татна уу.")
    subprocess.run(["git", "clone", "--depth", "1", MMEVAL_REPO, str(dest)], check=True)
    print("  ! Лиценз репод заагаагүй — тайландаа ашиглахаас өмнө зохиогчоос асуугаарай.")


def get_im2latex(out: Path, args) -> None:
    d = out / "im2latex_100k"
    for name in IM2LATEX_LISTS:
        download(IM2LATEX_BASE + name + "?download=1", d / name)
    if args.images:
        download(IM2LATEX_BASE + IM2LATEX_IMAGES + "?download=1", d / IM2LATEX_IMAGES)
        print(f"  Задлах: tar -xzf {d / IM2LATEX_IMAGES} -C {d}")
    else:
        print("  (зураг татсангүй — хэрэгтэй бол --images нэм)")


def get_tesseract(out: Path, args) -> None:
    download(TESS_MON_URL, out / "tesseract" / "mon.traineddata")
    print("  Тэмдэглэл: энэ файлыг tesseract-ийн tessdata хавтас руу хуулах эсвэл "
          "--tessdata-dir-ээр зааж өгнө.")


def get_assist09(out: Path, args) -> None:
    download(ASSIST09_PYBKT_URL, out / "assistments_2009" / "as_pybkt.csv")
    print("  Энэ нь pyBKT-ийн цэвэрлэсэн хувилбар. Бүрэн хувилбарыг сайтаас гараар татна.")


TASKS = {
    "math":      ("MATH (Hendrycks) — geometry/number_theory-гүй", get_math),
    "gsm8k":     ("GSM8K", get_gsm8k),
    "mmeval":    ("MM-Eval (git clone)", get_mmeval),
    "im2latex":  ("im2latex-100k (--images бол зураг ч бас)", get_im2latex),
    "tesseract": ("Tesseract mon.traineddata", get_tesseract),
    "assist09":  ("ASSISTments 2009 (pyBKT хувилбар)", get_assist09),
}


def main():
    p = argparse.ArgumentParser(description="Capstone II dataset татагч")
    p.add_argument("--out", default="data/raw", help="хадгалах хавтас (анхдагч: data/raw)")
    p.add_argument("--only", nargs="+", choices=TASKS.keys(), help="зөвхөн эдгээрийг татах")
    p.add_argument("--images", action="store_true", help="im2latex-ийн томьёоны зургийг татах")
    p.add_argument("--list", action="store_true", help="жагсаалт харуулаад гарах")
    args = p.parse_args()

    if args.list:
        for key, (desc, _) in TASKS.items():
            print(f"  {key:10s} {desc}")
        return

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    selected = args.only or list(TASKS)
    failed = []

    for key in selected:
        desc, fn = TASKS[key]
        print(f"\n[{key}] {desc}")
        try:
            fn(out, args)
        except Exception as e:  # нэг нь унавал бусад нь үргэлжилнэ
            print(f"  ✗ АЛДАА: {e}")
            failed.append(key)

    print("\n" + "=" * 50)
    print(f"Амжилттай: {len(selected) - len(failed)}/{len(selected)}  →  {out.resolve()}")
    if failed:
        print("Амжилтгүй: " + ", ".join(failed))
        print("Дахин оролдох:  python download_datasets.py --only " + " ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()