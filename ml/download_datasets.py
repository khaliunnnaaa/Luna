"""
Capstone II — Математик сурахад туслах ухаалаг веб систем
Нээлттэй dataset-уудыг автоматаар татах скрипт.

Ажиллуулах (Mac Terminal дээр, энэ файл байгаа хавтсанд):
    pip install datasets pandas requests
    python3 download_datasets.py            # жижиг/дунд хэмжээтэйг татна
    python3 download_datasets.py --images   # + im2latex-ийн зургууд (~1 GB)

Гараар татах шаардлагатай dataset-уудыг (бүртгэл, Google Drive, Kaggle)
dataset_catalog.xlsx файлын "Татах арга" баганаас харна уу.
"""
import argparse
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent / "data"

# MATH (Hendrycks) сэдвийг манай системийн сэдвийн кодтой холбох
# (бодлогын_сан.xlsx -> "Сэдвүүд" хуудас)
MATH_SUBJECT_MAP = {
    "prealgebra": "T01;T02",
    "algebra": "T03;T04;T05;T07;T08",
    "intermediate_algebra": "T04;T05;T06",
    "precalculus": "T06;T09",
    "counting_and_probability": "T10",
    "number_theory": "(хамрах хүрээнээс гадуур)",
    "geometry": "(хамрах хүрээнээс гадуур)",
}


def download(url: str, dest: Path, desc: str) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  [алгасав] {desc} аль хэдийн байна")
        return True
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        print(f"  [OK] {desc} -> {dest.relative_to(ROOT.parent)}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  [АЛДАА] {desc}: {e}")
        return False


def get_math():
    """MATH: 12,500 бодлого, 7 сэдэв, 5 түвшин (MIT)."""
    print("\n[1] MATH (Hendrycks) — бодлого ангилагчийн суурь өгөгдөл")
    try:
        from datasets import load_dataset
        import pandas as pd
    except ImportError:
        print("  pip install datasets pandas  гэж суулгана уу")
        return
    out = ROOT / "classifier" / "math_hendrycks.csv"
    if out.exists():
        print("  [алгасав] аль хэдийн байна")
        return
    frames = []
    for subj, ours in MATH_SUBJECT_MAP.items():
        for split in ("train", "test"):
            ds = load_dataset("EleutherAI/hendrycks_math", subj, split=split)
            df = ds.to_pandas()
            df["subject"] = subj
            df["split"] = split
            df["our_topics"] = ours
            frames.append(df)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(frames).to_csv(out, index=False)
    print(f"  [OK] {out.relative_to(ROOT.parent)}")


def get_gsm8k():
    """GSM8K: 8.5K бага ангийн үгэн бодлого (MIT)."""
    print("\n[2] GSM8K — үгэн бодлого")
    try:
        from datasets import load_dataset
    except ImportError:
        return
    out = ROOT / "classifier" / "gsm8k.csv"
    if out.exists():
        print("  [алгасав] аль хэдийн байна")
        return
    import pandas as pd
    parts = []
    for split in ("train", "test"):
        df = load_dataset("openai/gsm8k", "main", split=split).to_pandas()
        df["split"] = split
        parts.append(df)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(parts).to_csv(out, index=False)
    print(f"  [OK] {out.relative_to(ROOT.parent)}")


def get_mm_eval():
    """MM-Eval: монгол хэл дээрх 250 математик үгэн бодлого (reasoning хэсэг)."""
    print("\n[3] MM-Eval — монгол хэлний математик бодлого")
    for branch in ("main", "master"):
        url = f"https://raw.githubusercontent.com/joenahm/MM-Eval/{branch}/reasoning_eval.json"
        if download(url, ROOT / "mongolian" / "mm_eval_reasoning.json", "MM-Eval reasoning"):
            return


def get_assistments_pybkt():
    """ASSISTments 2009 (pyBKT-ийн бэлэн хувилбар) + Cognitive Tutor."""
    print("\n[4] ASSISTments / Cognitive Tutor — Knowledge Tracing (pyBKT формат)")
    base = "https://raw.githubusercontent.com/CAHLR/pyBKT-examples/master/data"
    download(f"{base}/as.csv", ROOT / "knowledge_tracing" / "assistments_pybkt.csv", "ASSISTments (as.csv)")
    download(f"{base}/ct.csv", ROOT / "knowledge_tracing" / "cognitive_tutor_pybkt.csv", "Cognitive Tutor (ct.csv)")


def get_im2latex(with_images: bool):
    """im2latex-100k: хэвлэмэл томьёоны зураг <-> LaTeX (Zenodo 56198)."""
    print("\n[5] im2latex-100k — OCR/томьёо таних")
    try:
        meta = requests.get("https://zenodo.org/api/records/56198", timeout=60).json()
    except Exception as e:  # noqa: BLE001
        print(f"  [АЛДАА] Zenodo: {e}")
        return
    for f in meta.get("files", []):
        name = f["key"]
        url = f["links"]["self"]
        size_mb = f.get("size", 0) / 1e6
        is_image = name.endswith((".tar.gz", ".tgz", ".zip"))
        if is_image and not with_images:
            print(f"  [алгасав] {name} ({size_mb:.0f} MB) — татах бол --images")
            continue
        download(url, ROOT / "ocr" / "im2latex_100k" / name, f"{name} ({size_mb:.1f} MB)")


def get_tesseract_mon():
    """Tesseract-ийн монгол хэлний загвар (Apache-2.0)."""
    print("\n[6] Tesseract mon.traineddata (tessdata_best)")
    download(
        "https://github.com/tesseract-ocr/tessdata_best/raw/main/mon.traineddata",
        ROOT / "ocr" / "tesseract" / "mon.traineddata",
        "mon.traineddata",
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--images", action="store_true", help="im2latex зургуудыг татах (~1 GB)")
    args = p.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    get_math()
    get_gsm8k()
    get_mm_eval()
    get_assistments_pybkt()
    get_im2latex(args.images)
    get_tesseract_mon()
    print("\nДууслаа. Гараар татах жагсаалтыг dataset_catalog.xlsx-ээс харна уу.")


if __name__ == "__main__":
    sys.exit(main())
