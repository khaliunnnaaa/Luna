# CLAUDE.md — Luna: Математик сурахад туслах ухаалаг веб систем (Capstone II)

Хэрэглэгч монголоор (заримдаа латин үсгээр: "hiij ehley", "or") бичдэг. Хариултыг монгол кириллээр өгнө.
Код/README-ийн тайлбар монголоор, хувьсагч/функцийн нэр англиар. Шаардлагын эх баримт:
«Системийн ерөнхий шаардлага ба цар хүрээ» (.docx) — FR-01…16, NFR-01…08; түүнтэй харьцуулсан
төлөв `docs/gap-analysis.md`-д.

**Гол зарчим (баримтаас):** хариу биш, чиглүүлэг — систем бодлогыг сурагчийн өмнөөс бодохгүй;
зөв хариуг API хэзээ ч сурагчид буцаахгүй; тайлбар богино; алдаа = дараагийн алхмын дохио.

## Бүтэц

```
backend/   FastAPI + SQLAlchemy 2 + Alembic, Python 3.11 (.venv), SQLite dev / PostgreSQL docker
frontend/  Next.js 15 (app router) + React 19 + KaTeX, энгийн CSS (globals.css), UI сангүй
ml/        ML хэсэг (тусдаа .venv, numpy<2, sklearn<1.7) — өөрийн CLAUDE.md-тэй, заавал унш
data/      сэдвийн граф, толь; data/ocr_images/ хоосон (зураг Drive-д)
docs/      architecture.md, CONTRIBUTING.md, gap-analysis.md (шаардлага ↔ код, явцын тэмдэглэл)
```

## Орчин ба командууд

```bash
# backend (хавтас: backend/, venv заавал идэвхжүүл — шинэ terminal-д pytest олдохгүй)
source .venv/bin/activate
pytest -q                    # 93+ тест, in-memory SQLite
ruff check .                 # line-length 100, select E,F,I,UP,B; B008 нь FastAPI Depends-д тохирдог
uvicorn app.main:app --reload
python -m app.seed           # ml/csv/*.csv → DB (сэдэв, толь, бодлого); дахин ажиллуулахад шинэчилнэ
python -m app.create_admin admin@example.com "НууцҮг" "Админ"
alembic upgrade head         # шинэ DB
alembic stamp head           # dev.db-д create_all аль хэдийн хүснэгт үүсгэсэн бол ("table already exists")

# frontend
npm run dev / npm run lint / npm run build

# ml (ml/CLAUDE.md-г үз)
python3 tools/build_bank.py  # бодлогын сан: SymPy шалгалт → бодлогын_сан.xlsx + csv/
```

`init_dev_db()` (database.py) зөвхөн SQLite дээр `create_all` хийнэ — dev.db-д хүснэгт өөрөө үүснэ.
PostgreSQL (docker) дээр зөвхөн Alembic: `backend/docker-entrypoint.sh` → `alembic upgrade head`.
Docker backend-д `./ml` → `/ml:ro` mount (seed, bkt_params зам). Docker Mac дээр суусан.
**DB = Supabase** (Session pooler, `?sslmode=require`); локал `db` нь `--profile localdb`.
Шинэ хүснэгтийн migration-д `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` заавал (0005-г үз). Хүснэгт нэмэхдээ **хоёуланг нь**: model + migration.

## Өгөгдлийн сан (backend/app/models/)

| Хүснэгт | Файл | Юу |
|---|---|---|
| users | user.py | role: student / parent / admin (Enum, нэрээр хадгална) |
| topics, topic_prerequisites, terms, problems | content.py | FR-16. `Topic.id` = ML-тэй ижил "T01".."T10". `Problem.answers` JSON (SymPy хэлбэр), `hints` ≤3, `terms` |
| attempts | learning.py | хариулт бүр: is_correct, error_type, hints_used, mastery_before/after |
| mastery | learning.py | (user_id, topic_id) PK, p_mastery (BKT), attempts/correct count |
| term_clicks, uploads, parent_child_links | learning.py | FR-05 дохио, FR-03 зураг (хараахан ашиглаагүй), FR-14 (хараахан ашиглаагүй) |
| placement_sessions | learning.py | FR-02 тестийн явц: items JSON, topic_queue, difficulty |

Migration: `0001_initial`, `0002_learning_tables`, `0003_placement`, `0004_solution_steps`,
`0005_enable_rls` (Supabase). Хариу/сануулга/mastery-ийн
ID, код бүгд ML хэсэгтэй нийцдэг (T01-001 … бодлогын код, T01..T10 сэдэв, түвшин 1–3).

## API (backend/app/api/)

- `auth.py` FR-01: register/login/me, argon2 + JWT. `deps.require_role(Role.admin)`.
- `content.py` FR-16: `/admin/{topics,terms,problems}` CRUD (зөвхөн админ), `GET /topics` нээлттэй.
  Сэдвийн prerequisite цикл шалгалт (`services/topic_graph.py`), хариу SymPy-д уншигдах эсэх шалгалт.
- `learning.py` сурагчийн урсгал:
  - `GET /problems/{id}` — **answers, hints байхгүй** харагдац (`ProblemStudentOut`)
  - `GET /problems/{id}/hints/{1..3}` — FR-06 шатлан сануулга
  - `POST /problems/{id}/attempt` {answer, hints_used} — FR-10 SymPy шалгалт + алдааны төрөл
    + FR-08 BKT mastery шинэчлэл. **Аль хэдийн бодсон бодлогод mastery өөрчлөгдөхгүй.** Зөвхөн student.
  - `GET /next[?topic_id=]` — FR-09 санал болгогч (`services/recommender.py`), FR-11 сэдэв сонгох
  - `GET /terms`, `POST /term-clicks` — FR-05; `GET /me/mastery`, `GET /me/attempts`
- `placement.py` FR-02: `GET /placement`, `POST /placement/{start,answer,finish}`.
- `uploads.py` FR-03/04: `POST /uploads` (multipart jpg/png ≤10MB → storage → ML /ocr → /classify),
  `PUT /uploads/{id}` засаад дахин ангилах, `GET /uploads/{id}/image` зөвхөн эзэмшигч, `DELETE` (NFR-06),
  `POST /classify {text}`, `GET /ml/health`. ML унтарсан бол status=failed + гараар бичих (NFR-07).
  FR-07: `POST /similar` → жишээ бодлого + `solution_steps` (сурагчийн харагдацад хэзээ ч өгөхгүй),
  `POST /uploads/{id}/outcome`. Алхмуудын эх: `ml/tools/bank_steps.py` (код → алхмууд).

## Сервисүүд (backend/app/services/)

- `answer_checker.py` — `is_equivalent`, `check_answer(student, answers) -> (ok, error_type)`.
  parse_expr-ийг тэмдэгтийн шүүлтүүр + builtins хоосон dict-ээр хамгаалсан. Хариуны хэлбэр:
  илэрхийлэл `2*sqrt(2)`, жагсаалт `[3, 4]` (дараалал хамаагүй), цэг `(2, -3)`, систем `{x: 7, y: 3}`,
  завсар `Interval.open(2, oo)`, `Union(...)`. Алдааны төрөл: empty / unparsable / sign_error / partial / wrong
  + `ERROR_FEEDBACK` монгол мессеж (зөв хариуг задруулахгүй).
- `mastery.py` — BKT, `ml/ml/tracing/mastery.py`-тэй ижил томьёо; параметр `ml/config/bkt_params.yaml`
  (`settings.bkt_params_path`), байхгүй бол `DEFAULT_PARAMS`. `MASTERED = 0.95`. [EPS, 1−EPS] хязгаар.
- `recommender.py` — prerequisite топологи → нээлттэй сэдэв (урьдач бүгд ≥0.95, өөрөө <0.95) →
  mastery→түвшин (<0.5→1, <0.8→2, бусад→3) → бодоогүй бодлого түрүүлнэ; бүгд эзэмшигдсэн бол давтлага.
  Сурагчийн анги (grade) одоогоор тооцдоггүй (User-д grade багана байхгүй) — ML хувилбараас ялгаатай.
- `ml_client.py` — `settings.ml_service_url` (default localhost:8001, docker: http://ml:8001); алдаа → None.
- `storage.py` — `S3_ENDPOINT` тохируулсан бол MinIO/S3 (boto3), үгүй бол `backend/uploads/` (gitignore).
- `placement.py` — сэдэв бүрээс 1 асуулт (≤10, топологи дараалал), 2-р түвшнээс эхэлж зөв/буруугаар ±1,
  "мэдэхгүй" = хоосон хариу, 10 мин. Дуусахад анхны mastery: зөв {1:.60, 2:.75, 3:.90}, буруу {1:.15, 2:.30, 3:.45}.
  Placement-ийн хариулт `attempts`-д орохгүй (BKT давхар тоолохгүй).

## Frontend (frontend/)

- `lib/api.ts` — бүх төрөл + `api.get/post/put/del`, token localStorage. Шинэ endpoint → эндээс төрөл нэм.
- `components/MathText.tsx` — `$...$` хэсгийг KaTeX. `components/ProblemSolver.tsx` — бодлого бодох
  дэлгэц (нэр томьёо дарах → тайлбар + term-click, сануулга шатлан, хариу, mastery бар).
- Хуудас: `/dashboard` (эзэмшлийн самбар + placement сануулга), `/practice[?topic=]`, `/problems/[id]`,
  `/placement`, `/admin/*` (FR-16). `useSearchParams` ашиглавал `<Suspense>`-д боох (build шаарддаг).
- CSS класс: `.student`, `.card.wide`, `.bar/.bar-fill`, `.mastery-row`, `.solver`, `.term` — globals.css.

## Ажлын явц ба дүрэм

- Commit: Conventional Commits, монгол тайлбар (`feat: сурагчийн урсгал (FR-02,05,…)`). `main`-д шууд
  push хийж байгаа (ганц хүний төсөл); CI: ruff + pytest + next lint/build.
- **Энэ орчны хязгаар:** Claude-ийн ажиллах орчноос PyPI/npm хаалттай тул backend тест, frontend
  build-ийг хэрэглэгч Mac дээрээ ажиллуулж үр дүнг хуулж өгдөг. Claude: syntax (`py_compile`), ruff,
  SymPy/BKT-ийн логикийг энд шалгадаг; FastAPI тестийг хэрэглэгчээр ажиллуулна.
- Шинэ FR хийхдээ: model + migration → service (цэвэр логик, тестлэхэд амар) → api + schema →
  tests/ → lib/api.ts төрөл → хуудас → README-ийн API хүснэгт, docs/gap-analysis.md "Явц".
- Метрик, тоог зохиож бичихгүй — зөвхөн бодитоор ажиллуулсан үр дүн (ml/CLAUDE.md-тэй ижил дүрэм).
- Нууц: token/нууц үгийг чат, notebook, кодонд бичихгүй; subprocess алдааны мессежэнд URL бүү хэвлэ
  (ocr_colab notebook-д нэг удаа алдсан, зассан).

## Хийгдсэн (2026-10-09 байдлаар)

FR-01 ✅ FR-02 ✅ FR-05 ✅ FR-06 ✅ FR-08 ✅ FR-09 ✅ FR-10 ✅ FR-11 🟡 (сэдэв сонгох бий, граф зураг үгүй)
FR-12 🟡 (самбар бий, график үгүй) FR-16 ✅. FR-03 ✅ (OCR нарийвчлал хэмжээгүй) FR-04 ✅ — `ml/service.py` HTTP сервис (8001), backend `services/ml_client.py` + `api/uploads.py`, frontend `/upload`.
FR-07 ✅ (`services/similar.py`, `/similar`, `bank_steps.py` 200 бодолт). FR-13, FR-14, FR-15 ❌. Дэлгэрэнгүй: docs/gap-analysis.md.

Бодлогын сан: 200 (сэдэв бүрт 20) — `ml/tools/bank_data.py` (60) + `bank_data_extra.py` (140),
`build_bank.py` SymPy 200/200. DB-д seed хийгдсэн. Ангилагч 200 дээр дахин сургагдсан (2026-10-09):
сэдэв macro-F1 0.931±0.031 (өмнө 0.907), түвшин 0.559 (өмнө 0.412), дэд сэдэв kNN top-1 0.653 (n=176;
26 дэд сэдэв ганц бодлоготой тул — шошгыг нэгтгэх хэрэгтэй). MATH сул шошго Mac дээр татагдаагүй (C = B).

OCR: `ml/notebooks/ocr_colab.ipynb` (Colab GPU) — шошголох ноорог, үнэлгээ, синтетик өгөгдөл,
pix2tex fine-tune; fine-tune жинг `PIX2TEX_CHECKPOINT`/`PIX2TEX_CONFIG` env-ээр `pipeline.py` ачаална.
Зураг 0/300 — хэрэглэгч цуглуулж байгаа.

## Дараагийн алхмууд (санал болгосон дараалал)

1. `python -m app.seed` + `ml.classifier.train` (200 бодлого) → шинэ метрик
2. ~~ML сервис + /uploads~~ ✅ (2026-10-09). Үлдсэн: OCR-ийн бодит нарийвчлал (Colab), pix2tex жинг ml сервист өгөх
3. ~~FR-07~~ ✅. Дэд сэдвийн нэрийг нэгтгэх (kNN top-1 0.65) — /similar-ийн чанарт нөлөөлнө
4. FR-12 график, FR-13 badge/streak, FR-14 эцэг эх (parent_child_links бэлэн)
5. User.grade багана → recommender-т ангийн давуу эрэмбэ (ML хувилбартай адил)
