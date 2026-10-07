# Ухаалаг математик 🧮

Математик сурахад туслах ухаалаг веб систем (Capstone II төсөл).
**Хариу биш, чиглүүлэг:** бодлогын зургийг таньж, сурагч яг аль ойлголтыг мэдэхгүй байгааг ML-ээр тодорхойлж, алхам алхмаар чиглүүлнэ.

## Бүтэц

```
backend/    FastAPI API (auth, тест, дасгал, хариу шалгагч)
frontend/   Next.js + KaTeX
ml/         OCR, сэдэв ангилагч, Knowledge Tracing, санал болгогч
data/       Сэдвийн граф, нэр томьёоны толь, бодлогын сан
docs/       Архитектур, хамтран ажиллах дүрэм
scripts/    Туслах скриптүүд (GitHub issue үүсгэх г.м.)
```

## Эхлүүлэх

```bash
cp .env.example .env
docker compose up --build
```

| Сервис | Хаяг |
|---|---|
| Frontend | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| MinIO консол | http://localhost:9001 |

Docker-гүйгээр:

```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
```

## Технологи

Next.js · KaTeX · FastAPI · PostgreSQL · MinIO/S3 · PyTorch · scikit-learn · Tesseract · pix2tex · pyBKT · SymPy · Docker

## Хөгжүүлэлтийн үе шат

1. Өгөгдөл ба суурь → 2. Цөм функц (FR-01, 02, 09, 10, 16) → 3. ML (FR-03, 04, 08) →
4. Зааварчилгаа (FR-05–07) → 5. Сэдэл ба эцэг эх (FR-11–15) → 6. Туршилт ба үнэлгээ

Дэлгэрэнгүй: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md), [docs/architecture.md](docs/architecture.md)
