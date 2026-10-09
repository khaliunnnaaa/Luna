# CLAUDE.md — Capstone II: Математик сурахад туслах ухаалаг веб систем (ML хэсэг)

Хэрэглэгч монголоор (заримдаа латин үсгээр) бичдэг. Хариултыг монгол кириллээр өгнө.
10–12-р ангийн сурагчдад зориулсан системийн **зөвхөн ML хэсэг** (1-р үе шат). Веб UI/backend
дараа нь хийгдэх бөгөөд ML-ийг зөвхөн `ml/api.py`-ээр дуудна. Luna git репогийн `ml/` хавтас (backend нь `../backend`, frontend нь `../frontend`).

## Заавал мөрдөх дүрэм (даалгаврын эх бичгээс)
- Метрикийн утгыг **хэзээ ч зохиож бичихгүй**, зөвхөн бодитоор ажиллуулсан үр дүнг тайлагнана.
- Зорилтод хүрэхгүй бол зорилтыг өөрчлөхгүй, шалтгаан ба сайжруулах саналыг бичнэ.
- Файл дутуу, эсвэл бүтэц нь хүлээгдсэнээс өөр бол таамаглахгүй, хэрэглэгчээс асууна.
- Код/README-ийн тайлбар монголоор, хувьсагч/функцийн нэр англиар. Random seed = 42.
- CPU дээр хэдхэн минутад ажиллах ёстой. GPU шаардлагагүй.
- **Энэ үе шатанд хийхгүй:** алдааны төрөл ангилах (FR-10), DKT, алхамчилсан зааварчилгаа (FR-06/07), веб UI.
- Модуль бүрийн дараа тестээ ажиллуулж, үр дүнг `reports/results.md`-д нэмнэ (`ml/report.py: update_section`).

## Орчин
- `ml/.venv` = **Python 3.11** (`/opt/homebrew/bin/python3.11`). Backend-ийн venv тусдаа (`../backend/.venv`).
- Ажиллуулахдаа үргэлж `.venv/bin/python -m ...` (модуль хэлбэрээр, төслийн үндсэн хавтаснаас).
- `scikit-learn<1.7`, `numpy<2`-оор хувилбарыг тогтоосон: pyBKT 1.4.3 нь шинэ хувилбаруудтай нийцэхгүй.
- pyBKT-ийг `parallel=False`-аар ажиллуулна: macOS spawn дээр pool гацдаг. pyBKT-ийг хэзээ ч stdin
  (`python - <<EOF`) дээрээс бүү ажиллуул, multiprocessing эцэс төгсгөлгүй давтагддаг.
- macOS дээр `timeout` команд байхгүй.

## Командууд
```bash
.venv/bin/python download.py                  # data/raw/ (каталогийн "Автомат" 6 dataset)
.venv/bin/python -m ml.classifier.train       # ~2 мин → models/*.joblib, reports/
.venv/bin/python -m ml.tracing.train_bkt      # ~6 мин → config/bkt_params.yaml (--max-skills N: хурдан туршилт)
.venv/bin/python -m ml.ocr.evaluate           # data/own_images/ байвал үнэлнэ
.venv/bin/python -m pytest -q tests           # 26 тест
.venv/bin/python demo.py                      # зохиомол сурагчийн демо
```

## Бүтэц
```
ml/common.py            зам, тогтмол, load_bank(), load_topics(), problem_input()
ml/report.py            reports/results.md-ийн хэсгүүдийг (data/classifier/tracing/recommender/ocr/summary) шинэчилнэ
ml/classifier/          features.py (LaTeX шинж), train.py, predict.py
ml/tracing/             train_bkt.py, mastery.py (BKT шинэчлэл, StudentStore/JSONStudentStore)
ml/recommender/         recommend.py (топологийн эрэмбэ, дүрэмд суурилсан санал)
ml/ocr/                 pipeline.py (Tesseract mon + pix2tex), evaluate.py (exact match, NED)
ml/api.py               classify_problem, update_mastery, recommend_next, recognize_image, register_student
config/                 topics.csv (prereq ";"-ээр), topic_mapping.yaml, bkt_params.yaml (train_bkt үүсгэнэ)
models/, state/, data/raw/   .gitignore-д орсон
```

## Өгөгдлийн тухай мэдэх зүйл
- `бодлогын_сан.xlsx` / "Бодлого" хуудас: **200 бодлого, сэдэв бүрт 20** (2026-10-09; өмнө 60). Эх сурвалж: `tools/bank_data.py` (эхний 60) + `tools/bank_data_extra.py` (+140), `python3 tools/build_bank.py`-аар xlsx/csv үүснэ. Баганууд: `id, сэдэв_код, дэд_сэдэв,
  түвшин(1-3), бодлогын_текст, томьёо_LaTeX, ...`. Хоосон мөр одоогоор алга (гэхдээ кодонд шүүлтүүр бий).
- **Хүндийн зэрэг 1–3** (1–5 биш). Хэрэглэгч 1–3-аар нь ашиглахыг баталсан. API `difficulty` нь 1–3 буцаана.
- Олон бодлогын текст ерөнхий ("Тэгшитгэлийг бод."), тул ангилагчийн оролт = текст + LaTeX.
- Бусад хуудас: Сэдвүүд, Сэдвийн_граф (11 ирмэг, `config/topics.csv`-тэй ижил, тестээр шалгадаг), Нэр_томьёо.
- ASSISTments (`data/raw/assistments_2009/as_pybkt.csv`, latin1): 525,534 мөр. Skill-гүй 78,690 ба
  давхардсан `(order_id, skill)` 121,207 мөрийг хасна → 325,637 мөр, 4,151 сурагч, 110 skill.
- MM-Eval нь сэдвийн шошгогүй тул ашиглаагүй. MATH: 9,742 бодлого (geometry/number_theory хассан).
- `data/` дотор `download_datasets.py`-ийн хуучин хуулбар (`data/classifier/` гэх мэт) болон im2latex-ийн
  зургийн архив (`data/ocr/im2latex_100k/formula_images.tar.gz`, задлаагүй) байна. ML код зөвхөн `data/raw/`-ийг ашиглана.

## Гол шийдвэрүүд
- Ангилагч: A = TF-IDF char_wb(2–5) + LR(C=10); B = A + LaTeX шинж (StandardScaler); C = B + MATH сул
  шошго (regex дүрэм `topic_mapping.yaml`, сэдэв бүрт ≤300, жин 0.1, тохируулаагүй). Үнэлгээ:
  RepeatedStratifiedKFold(3×10). CV-ийн дундаж macro-F1-ээр хамгийн сайныг сонгоод бүх өгөгдөл дээр сургана.
- BKT: сурагчаар 80/20 хуваана (GroupShuffleSplit, assert-аар шалгадаг). 110 skill-ийн медиан параметрийг
  T01–T10 бүрийн анхны утга болгоно (хэрэглэгчийн өгөгдөл одоогоор алга).
- Mastery-г [1e-4, 1−1e-4] завсарт хязгаарладаг. Яг 1.0 болчихвол буруу хариулт ч mastery-г бууруулж чадахгүй болдог (тестээр илэрсэн алдаа).
- Санал болгогч: урьдач сэдэв бүгд ≥0.95 бөгөөд өөрөө <0.95 сэдвүүдээс сурагчийн ангийнхыг түрүүлж,
  дараа нь топологийн эрэмбээр сонгоно. Түвшин: mastery <0.5→1, <0.8→2, бусад→3. Өмнө санал болгосныг давтахгүй.
- Сурагчийн төлөв: `state/students/<id>.json`. DB руу шилжихдээ `StudentStore`-ийг өвлөнө.

## Одоогийн үр дүн (2026-10-05, бодитоор ажиллуулсан)
| Модуль | Үр дүн |
|---|---|
| Сэдэв macro-F1 | A 0.757±0.049, B 0.897±0.067, **C 0.907±0.062** (сонгосон), dummy 0.107 |
| Түвшин macro-F1 | **B 0.412±0.079**, A 0.258, dummy 0.280 — сул |
| Дэд сэдэв kNN LOO | top-1 0.867, top-3 1.000 (30 бодлого) |
| BKT AUC | **0.7237** ✅ (≥0.70), baseline 0.627. Медиан: prior 0.667, learn 0.143, guess 0.146, slip 0.232 |
| Тест | 26/26 давсан |
| OCR | **Хэмжээгүй** |

Дэлгэрэнгүй: `reports/results.md`, `reports/*_metrics.json`, confusion matrix PNG.

## Хүлээгдэж буй / дараагийн алхам
1. **OCR:** `brew install tesseract` болон `pip install -r requirements-ocr.txt` (torch ~1 GB) суугаагүй.
   Хэрэглэгчээс зөвшөөрөл асуусан, хариу ирээгүй. `data/own_images/`-д зураг + ижил нэртэй `.tex` хос
   (≥300) бүрдүүлэх. Pipeline-ийг бодит зураг дээр хараахан туршаагүй.
2. BKT prior (0.667) өндөр тул сэдэв 1–2 зөв хариултаар "эзэмшсэн" болж байна. Түвшин тогтоох
   тестээр (FR-02) prior-ийг тохируулах эсвэл бууруулах.
3. Бодлогын санг өргөтгөх (сэдэв бүрт ≥30) ба бие даасан тест багц бүрдүүлэх. B/C ялгаа std-ээс бага.
4. Хүндийн зэргийн шинж сайжруулах (SymPy-гаар гаргасан зэрэг, гишүүний тоо, шийдлийн алхам).
5. Гараар татах dataset-ууд (MonMLU, Eedi, KDD Cup, Junyi) татагдаагүй, бүртгэл шаардлагатай.
6. `data/` дахь давхардсан хуучин өгөгдлийг (`download_datasets.py`-ийн) цэвэрлэх эсэхийг хэрэглэгч шийдээгүй.
