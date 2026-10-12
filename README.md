# Ухаалаг математик 🧮

Математик сурахад туслах ухаалаг веб систем (Capstone II төсөл).
**Хариу биш, чиглүүлэг:** бодлогын зургийг таньж, сурагч яг аль ойлголтыг мэдэхгүй байгааг ML-ээр тодорхойлж, алхам алхмаар чиглүүлнэ.

## Бүтэц

```
backend/    FastAPI API (auth, тест, дасгал, хариу шалгагч)
frontend/   Next.js + KaTeX
ml/         ML хэсэг: сэдэв ангилагч, BKT, санал болгогч, OCR + бодлогын сан (ml/csv)
data/       Сэдвийн граф, нэр томьёоны толь, бодлогын сан
docs/       Архитектур, хамтран ажиллах дүрэм
scripts/    Туслах скриптүүд (GitHub issue үүсгэх г.м.)
```

## Эхлүүлэх

```bash
cp .env.example .env          # DATABASE_URL (Supabase), JWT_SECRET-ийг бөглө
docker compose up --build     # backend эхлэхэд `alembic upgrade head` автоматаар ажиллана

# анх удаа: бодлогын сан ачаалах + админ үүсгэх
docker compose exec backend python -m app.seed
docker compose exec backend python -m app.create_admin admin@example.com "НууцҮг" "Админ"
```

### Өгөгдлийн сан: Supabase

1. supabase.com → New project (region: Singapore/Tokyo ойр). DB нууц үгийг хадгал.
2. **Connect → Session pooler** хаягийг `.env`-ийн `DATABASE_URL`-д
   (`postgresql+psycopg://...pooler.supabase.com:5432/postgres?sslmode=require`).
   Direct хаяг IPv6-only, Transaction pooler (6543) psycopg3/Alembic-тай таарахгүй.
3. `docker compose up` (эсвэл локал: `cd backend && alembic upgrade head && python -m app.seed`).
4. Migration `0005` бүх хүснэгтэд RLS асаана — Supabase-ийн REST API (anon key) өгөгдөл
   буцаахгүй, backend `postgres` эрхээр хэвийн ажиллана. Шинэ хүснэгт нэмбэл migration-д нь
   `ENABLE ROW LEVEL SECURITY` нэм.

Локал PostgreSQL ашиглах бол `.env`-д `@db:5432` хаягийг идэвхжүүлээд
`docker compose --profile localdb up`. Хуучин `create_all`-оор үүссэн DB-д "already exists" гарвал
`docker compose run --rm backend alembic stamp head`.

| Сервис | Хаяг |
|---|---|
| Frontend | http://localhost:3000 |
| ML сервис | http://localhost:8001/docs |
| API + Swagger | http://localhost:8000/docs |
| MinIO консол | http://localhost:9001 |

Docker-гүйгээр:

```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && uvicorn app.main:app --reload

cd frontend && npm install && npm run dev

cd ml && .venv/bin/uvicorn service:app --port 8001     # OCR/ангилал (байхгүй бол гараар бичих горим)
```

## Админ хэрэглэгч үүсгэх

Админ эрхээр сайтаас бүртгүүлэх боломжгүй. `backend` хавтсанд, venv идэвхтэй үед:

```bash
python -m app.create_admin admin@example.com "НууцҮг123" "Админ"
```

## Өгөгдлийн сангийн migration (Alembic)

`backend` хавтсанд, venv идэвхтэй үед:

```bash
alembic upgrade head                            # шинэ DB: бүх хүснэгт
alembic stamp head                              # локал dev.db: create_all аль хэдийн үүсгэсэн бол
alembic revision --autogenerate -m "тайлбар"    # model өөрчилсний дараа
```

Локал SQLite дээр `uvicorn`/seed асахад дутуу хүснэгтийг `create_all` автоматаар нэмдэг
(`init_dev_db`), тиймээс dev.db-д `upgrade` хийхэд "table already exists" гарвал `alembic stamp head`.
PostgreSQL (Docker) дээр `create_all` ажиллахгүй — зөвхөн Alembic (`backend/docker-entrypoint.sh`).

## API-ийн ерөнхий зураг

| Бүлэг | Endpoint | FR |
|---|---|---|
| auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | FR-01 |
| content | `GET /topics`, `GET /terms` (нээлттэй); `/admin/topics`, `/admin/terms`, `/admin/problems` CRUD | FR-11, FR-16 |
| learning | `GET /problems/{id}` (хариу, сануулгагүй), `GET /problems/{id}/hints/{1..3}` | FR-06 |
| learning | `POST /problems/{id}/attempt` → зөв/буруу, алдааны төрөл, mastery өмнө/дараа | FR-10, FR-08 |
| placement | `GET /placement`, `POST /placement/start`, `POST /placement/answer`, `POST /placement/finish` — 8–10 асуулт, adaptive, ≤10 мин | FR-02 |
| uploads | `POST /uploads` (зураг → OCR → ангилал), `PUT /uploads/{id}` (засах), `GET /uploads/{id}/image`, `DELETE`, `POST /classify`, `GET /ml/health` | FR-03, FR-04 |
| similar | `POST /similar {text, topic_id?, exclude}` — ижил төстэй бодлого + алхамчилсан бодолт; `POST /uploads/{id}/outcome` | FR-07 |
| learning | `GET /next`, `GET /next?topic_id=T04` → санал болгосон дасгал + шалтгаан | FR-09, FR-11 |
| learning | `POST /term-clicks`, `GET /me/mastery`, `GET /me/attempts` | FR-05, FR-08 |

Frontend хуудсууд: `/dashboard` (сэдвийн эзэмшил, статистик), `/practice` (санал болгосон дасгал),
`/practice?topic=T04` (сонгосон сэдвээс), `/problems/{id}` (тодорхой бодлого), `/placement` (түвшин тогтоох тест), `/upload` (зураг оруулах), `/similar` (ижил төстэй бодлогыг алхам алхмаар).

## Технологи

Next.js · KaTeX · FastAPI · PostgreSQL · MinIO/S3 · PyTorch · scikit-learn · Tesseract · pix2tex · pyBKT · SymPy · Docker

## Хөгжүүлэлтийн үе шат

1. Өгөгдөл ба суурь → 2. Цөм функц (FR-01, 02, 09, 10, 16) → 3. ML (FR-03, 04, 08) →
4. Зааварчилгаа (FR-05–07) → 5. Сэдэл ба эцэг эх (FR-11–15) → 6. Туршилт ба үнэлгээ

Дэлгэрэнгүй: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md), [docs/architecture.md](docs/architecture.md)
