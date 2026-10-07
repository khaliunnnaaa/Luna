# Capstone II — Математик сурахад туслах ухаалаг веб систем: ML хэсэг

> Luna репогийн `ml/` хавтас. Эх хувилбар: `~/Documents/capstone_datasets` (2026-10-07-нд хуулсан).
> Том өгөгдөл (`data/`), сургасан загвар (`models/`), сурагчийн төлөв (`state/`) git-д орохгүй.
> `models/` байхгүй бол `python -m ml.classifier.train`, `data/raw/` байхгүй бол `python download.py`.

10–12-р ангийн сурагчдад зориулсан системийн machine learning хэсэг (1-р үе шат).
Веб UI ба backend нь энэ хэсгийг зөвхөн `ml/api.py`-ээр дуудна. Бодит үр дүн, метрик:
[`reports/results.md`](reports/results.md).

## Хурдан эхлэх

```bash
cd ~/Documents/GitHub/Luna/ml
/opt/homebrew/bin/python3.11 -m venv .venv          # Python 3.10+
.venv/bin/pip install -r requirements.txt
.venv/bin/python download.py                         # data/raw/ (~120 MB)

.venv/bin/python -m ml.classifier.train              # ~2 мин  → models/, reports/
.venv/bin/python -m ml.tracing.train_bkt             # ~6 мин  → config/bkt_params.yaml
.venv/bin/python -m ml.ocr.evaluate                  # data/own_images/ байвал үнэлнэ
.venv/bin/python -m pytest tests
.venv/bin/python demo.py
```

Бүх зүйл CPU дээр ажиллана, random seed = 42.

## Бүтэц

```
ml/
  common.py          зам, бодлогын сан / сэдэв ачаалах
  classifier/        train.py, predict.py, features.py (LaTeX шинж)
  tracing/           train_bkt.py, mastery.py (BKT шинэчлэл + JSON хадгалалт)
  recommender/       recommend.py (дүрэмд суурилсан)
  ocr/               pipeline.py (pix2tex + Tesseract), evaluate.py
  api.py             ← веб backend дуудах цорын ганц цэг
config/              topics.csv, topic_mapping.yaml, bkt_params.yaml
models/              сургасан загвар (.joblib) — git-д орохгүй
reports/             results.md, *_metrics.json, confusion matrix зураг
state/students/      сурагчийн төлөв (JSON) — git-д орохгүй
tests/               pytest
demo.py              командын мөрийн демо
```

## API (`ml/api.py`)

```python
from ml.api import classify_problem, update_mastery, recommend_next, recognize_image

classify_problem("Тэгшитгэлийг бод. x^2-9=0")
# {"topic": "T04", "difficulty": 1, "confidence": 0.81}
update_mastery("s123", "T04", True)        # {"T01": 0.70, ..., "T04": 0.85, ...}
recommend_next("s123")                     # {"problem_id": "T04-020", "topic": "T04", "difficulty": 2, "reason": "..."}
recognize_image("photo.jpg")               # {"text": "...", "latex": ["x^2-9=0"]}
register_student("s123", grade=11)         # нэмэлт: ангийг тохируулах (анхдагч 10)
```

`difficulty` нь бодлогын сангийн `түвшин(1-3)` баганын дагуу **1–3** утгатай.

## Модулиуд

### 1. Бодлого ангилагч (FR-04)
Оролт нь `бодлогын_текст` + `томьёо_LaTeX`. Олон бодлогын текст ерөнхий ("Тэгшитгэлийг бод.")
тул сэдвийн гол дохио томьёонд байдаг. Гурван хувилбарыг харьцуулна:
- **A** — TF-IDF (тэмдэгтийн 2–5 n-gram) + LogisticRegression
- **B** — A + хэлнээс хамаарахгүй LaTeX шинж (`\frac`, `\sqrt`, `\log`, `\sin`, `^`, `=`, `<` ...; юникод √ ≤ π-г ижил тооцно)
- **C** — B + MATH (Hendrycks)-ийн сул шошготой бодлого (`config/topic_mapping.yaml`-ийн regex дүрмээр, жин 0.1)

Үнэлгээ: `RepeatedStratifiedKFold(3 fold × 10)`, macro-F1 дундаж ± std, confusion matrix.
Дэд сэдвийг хамгийн ойрын хөрш (kNN, cosine)-өөр санал болгоно.

### 2. Мэдлэг хянах — BKT (FR-08)
pyBKT-ээр ASSISTments 2009 дээр сургаж, train/test-ийг **сурагчаар** хуваана (data leakage-гүй).
Давхардсан `(order_id, skill)` мөрүүдийг хасна.

**Анхны параметрийн шийдвэр.** Манай системд одоогоор хэрэглэгчийн хариултын түүх байхгүй тул
T01–T10 сэдэв бүрт тусгайлан параметр сургах боломжгүй. Иймд ASSISTments-ийн бүх математикийн
skill-ийн сурсан параметрийн (prior, learn, guess, slip) **медианыг** сэдэв бүрийн анхны утга болгож
`config/bkt_params.yaml`-д хадгалсан. Медиан нь дундажаас ялгаатай нь цөөн хэт утгатай skill-д
(жишээ нь learn ≈ 1) мэдрэг биш. Энэ бол түр шийдэл: систем ашиглагдаж хариулт хуримтлагдсаны
дараа сэдэв тус бүрээр дахин сургана. `bkt_params.yaml`-ийн `topics` хэсгийг сэдвээр нь
тусад нь засах боломжтой.

Mastery-г [0.0001, 0.9999] завсарт хязгаарладаг. Яг 1.0 болчихвол буруу хариулт ч mastery-г
бууруулж чадахгүй болдог.

Сурагчийн төлөв `state/students/<id>.json`-д хадгалагдана. Хадгалалт нь `StudentStore`
интерфейсээр тусгаарлагдсан тул өгөгдлийн сан руу шилжихэд зөвхөн шинэ класс бичихэд хангалттай.

### 3. Дараагийн бодлого санал болгогч (FR-09/11)
`config/topics.csv`-ийн `prereq` баганаас граф уншина (цикл байвал алдаа өгнө, тестээр шалгадаг).
Урьдач сэдвүүд нь эзэмшигдсэн (mastery ≥ 0.95) боловч өөрөө эзэмшигдээгүй сэдвүүдээс сурагчийн
ангийнхыг түрүүлж, топологийн дарааллаар сонгоно. Mastery-д тохирох түвшний (< 0.5 → 1,
< 0.8 → 2, бусад → 3), өмнө санал болгоогүй бодлогыг сонгож шалтгааныг (`reason`) хамт буцаана.

### 4. OCR (NFR-05)
Шинээр сургахгүй: Tesseract (`mon.traineddata`) нь монгол текстийг, pix2tex нь томьёог танина.
Кириллгүй, математикийн тэмдэгттэй үгсийн мужийг тайрч pix2tex-д өгнө.

```bash
brew install tesseract
.venv/bin/pip install -r requirements-ocr.txt   # torch татна (~1 GB)
```

Үнэлгээ: `data/own_images/`-д зураг (`.jpg/.png`) ба ижил нэртэй `.tex` файл тавиад
`python -m ml.ocr.evaluate`. Метрик нь exact match болон normalized edit distance.

## Хувилбарын тэмдэглэл
- `scikit-learn<1.7`, `numpy<2`: pyBKT 1.4.3 нь шинэ хувилбарууд дээр унадаг.
- pyBKT-ийг `parallel=False`-аар ажиллуулна: macOS дээр multiprocessing pool гацдаг.

## Өгөгдөл

| Файл | Агуулга |
|---|---|
| `dataset_catalog.xlsx` | 15 нээлттэй dataset: ML бүрэлдэхүүн, хэмжээ, лиценз, линк, татах арга |
| `бодлогын_сан.xlsx` | 60 монгол бодлого (10 сэдэв × 3 түвшин), 3 шаттай сануулга, түгээмэл алдаа, сэдвийн граф, 32 нэр томьёо |
| `csv/` | Бодлогын сан CSV хэлбэрээр (PostgreSQL руу оруулахад) |
| `download.py` | Каталогийн "Автомат" dataset-уудыг `data/raw/` руу татна (ML хэсэг үүнийг ашиглана) |
| `download_datasets.py` | Хуучин хувилбар: `data/classifier/` гэх мэт хавтас руу CSV-ээр татна |
| `tools/` | Бодлогын санг засах (`bank_data.py`) → SymPy-аар шалгаад дахин үүсгэх (`build_bank.py`) |

Каталогт "Гараар" гэсэн dataset-уудад бүртгэл (Kaggle, DataShop, TC11) хэрэгтэй.

### Бодлого нэмэх
`tools/bank_data.py` дахь `P` жагсаалтад шинэ мөр нэмээд `python3 tools/build_bank.py` ажиллуул.
Энэ нь хариуг SymPy-аар шалгаж, Excel/CSV-г дахин үүсгэнэ. Дараа нь ангилагчийг дахин сургана.
