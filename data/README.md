# Өгөгдөл

**Бодлогын сангийн үндсэн эх сурвалж нь `ml/csv/`** (ML хэсэгтэй нэг эх сурвалж):

| Файл | Агуулга |
|---|---|
| `ml/csv/topics.csv` | 10 сэдэв (T01–T10), өмнөх сэдвийн холбоо (`prereq`, `;`-ээр) |
| `ml/csv/problems.csv` | 60 бодлого: текст, LaTeX, SymPy хариу, 3 сануулга, түгээмэл алдаа, нэр томьёо |
| `ml/csv/glossary.csv` | 32 нэр томьёо |

Backend-ийн сан руу ачаалах: `cd backend && python -m app.seed`

Бодлого нэмэх хоёр арга:
1. Админы хуудас (`/admin`) — шууд сан руу.
2. `ml/tools/bank_data.py`-д нэмээд `python3 ml/tools/build_bank.py` → CSV/Excel дахин үүснэ → `python -m app.seed`.
   ML ангилагчийг дахин сургахад энэ арга хэрэгтэй.

- `ocr_images/` — OCR үнэлгээний зураг (git-д оруулахгүй, `ml/data/own_images/` руу хийнэ).
