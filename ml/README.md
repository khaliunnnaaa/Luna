# ML бүрэлдэхүүн

| Хавтас | Үүрэг | Арга | Зорилтот үзүүлэлт |
|---|---|---|---|
| `src/ocr` | Зураг → текст + LaTeX (FR-03) | Tesseract `mon` + pix2tex, fine-tune | Томьёо зөв танилт ≥ 85% |
| `src/classifier` | Бодлогын сэдэв ангилах (FR-04) | TF-IDF + LogReg → multilingual BERT | Accuracy ≥ 80% |
| `src/knowledge_tracing` | Эзэмшлийн магадлал (FR-08) | pyBKT → DKT | AUC ≥ 0.70 |
| `src/recommender` | Дараагийн дасгал (FR-09) | Prerequisite граф + BKT | — |

- `notebooks/` — туршилт, EDA, үнэлгээ.
- `models/` — сургасан жингүүд (git-д орохгүй, `.gitignore`).
