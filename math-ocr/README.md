# Math OCR — Монгол бодлогын зураг → текст + LaTeX

"Математик сурахад туслах ухаалаг веб систем" (Capstone II)-ийн **OCR бүрэлдэхүүн**.
Шаардлагын баримтын 5-р хэсэгт заасан **Tesseract (mon) + pix2tex** хослолоор хийгдсэн.

| Шаардлага | Энд хэрхэн шийдсэн |
|---|---|
| **FR-03** Зураг → текст ба томьёо, засварлах боломж | `MathOCR` нь `markdown` (`Бод: $x^2-5x+6=0$`) болон бүс бүрийн `bbox`, `conf`, `needs_review`-ийг буцаана. Frontend эргэлзээтэй бүсийг тодруулж засуулна |
| **NFR-02** OCR ≤ 5 сек | Хугацааны төсөв (`OCR_BUDGET_S=5`). Хэтэрвэл үлдсэн томьёог хурдан fallback-аар бөглөнө. API талд 8 сек timeout |
| **NFR-05** Томьёо зөв танилт ≥ 85% | `eval/evaluate.py` нь PASS/FAIL болон алдааны CSV гаргана |
| **NFR-06** Нууцлал | Зургийг дискэнд хадгалахгүй, санах ойд боловсруулна |
| **NFR-07** ML унасан ч систем ажиллана | pix2tex/`mon` байхгүй бол fallback ажиллана. API 503/504 буцаахад backend гараар бичих горим руу шилжинэ |
| **7.3** Хэвлэмэл, нэг бодлоготой зураг | Зургийн чанарыг шалгадаг: бүдэг, харанхуй бол дахин авахыг хүснэ |

## Ажиллах зарчим

```
зураг ─► preprocess ─► Tesseract(mon) үг+bbox ─► layout ─┬─► текст бүс ─► монгол алдаа засвар ─┐
         (эргэлт, сүүдэр,                     (текст/томьёо│                                    ├─► markdown + JSON
          хазайлт, үсгийн                      ялгах,       └─► томьёо бүс ─► pix2tex ─► LaTeX ─┘
          өндрийг 32px болгох)                 бутархай илрүүлэх)
```

**Layout (`ocr/layout.py`)** нь хамгийн чухал хэсэг. Монгол бодлогод нэг мөрөнд текст, томьёо холилдсон байдаг, тиймээс:
1. Tesseract-ын уншсан үг бүрийг ангилна: итгэлцүүр ≥55 бөгөөд 2+ кирилл үсэгтэй бол **текст**. Нэг үсэг (`x`), латин үсэг, `=+^√`, `log/sin/tg` агуулсан бол **томьёо**. Тоо, цэг таслал хөршийнхөө ангиллыг авна.
2. **Бутархайн зураасыг** зургаас шууд илрүүлнэ (нимгэн хэвтээ шугам, дээр доор нь бэхтэй). Tesseract бутархайг 2-3 тусдаа мөр гэж уншдаг тул энэ алхам заавал хэрэгтэй.
3. Томьёоны хүрээг зэрэг, хуваарь, язгуурыг хамруулахаар тэлж, ойрхон хэсгүүдийг нэгтгэнэ.
4. (Заавал биш) YOLO төрлийн томьёо илрүүлэгч ONNX өгвөл (`MFD_ONNX=...`) байрлалыг түүгээр олно.

## Суулгах

```bash
# 1. Tesseract
#    Windows: https://github.com/UB-Mannheim/tesseract/wiki (суулгахдаа "Mongolian"-ийг сонго)
#    macOS:   brew install tesseract tesseract-lang
#    Ubuntu:  sudo apt install tesseract-ocr tesseract-ocr-mon
# 2. Python багцууд
pip install -r requirements.txt
# 3. mon.traineddata (best) + pix2tex жин
python -m tools.setup_models
```

Docker: `docker build -t math-ocr . && docker run -p 8001:8001 math-ocr`

## Ашиглах

```python
from ocr import MathOCR
ocr = MathOCR()
r = ocr("bodlogo.jpg")
print(r["markdown"])        # Тэгшитгэлийг бод: $x^{2}-5x+6=0$
```

API: `uvicorn api:app --port 8001` → `POST /ocr` (multipart `file`)

```json
{
  "markdown": "Тэгшитгэлийг бод: $x^{2}-5x+6=0$",
  "lines": [[
    {"type": "text", "content": "Тэгшитгэлийг бод:", "bbox": [40,52,300,80], "conf": 0.93, "needs_review": false},
    {"type": "formula", "content": "x^{2}-5x+6=0", "bbox": [310,44,560,86], "conf": 1.0, "needs_review": false}
  ]],
  "needs_review": false,
  "quality": {"sharpness": 412.3, "brightness": 221.0, "issues": []},
  "engines": {"text": "tesseract:mon+eng", "formula": "pix2tex", "detector": "heuristic"},
  "timing_ms": {"preprocess": 60, "layout": 380, "recognize": 900, "total": 1340}
}
```

Frontend (FR-03): `markdown`-ийг KaTeX-ээр харуулж, `needs_review: true` бүсийг шараар тодруулна. Томьёон дээр дарахад LaTeX засах талбар нээгдэнэ (жишээ нь MathLive). Сурагч баталгаажуулсны дараа FR-04 ангилагч руу илгээнэ.

## Өгөгдөл, fine-tune, үнэлгээ (шаардлагын 6-р хэсэг: ≥300 зураг)

```bash
# 1. Өөрсдийн авсан зургийг data/real/images/ руу хийгээд ноорог шошго үүсгэх
python -m tools.preannotate --images data/real/images --out data/real/labels_draft.jsonl
#    -> markdown, formulas[].latex талбарыг гараар засаад labels.jsonl нэрээр хадгална

# 2. train/val/test (70/15/15) болгож хуваах + pix2tex формат
python -m tools.split_dataset --data data/real

# 3. Синтетик өгөгдлөөр нэмэгдүүлэх (монгол текст + томьёо, камерын шуугиантай)
python -m tools.synth --out data/synth --n 3000

# 4. pix2tex fine-tune (GPU-тэй бол Colab дээр)
python -m pix2tex.dataset.dataset --equations data/real/pix2tex/train/math.txt \
       --images data/real/pix2tex/train --out data/train.pkl
python -m pix2tex.dataset.dataset --equations data/real/pix2tex/val/math.txt \
       --images data/real/pix2tex/val --out data/val.pkl
#    pix2tex/model/settings/config.yaml-ийг хуулж: data: data/train.pkl, valdata: data/val.pkl,
#    load_chkpt: <анхны weights.pth>, lr: 0.0001 -> 0.00005, epochs: 10-20
python -m pix2tex.train --config my_config.yaml
export PIX2TEX_CHECKPOINT=checkpoints/mn_math/mn_math_e10.pth PIX2TEX_CONFIG=my_config.yaml

# 5. Үнэлгээ — тайландаа fine-tune хийхээс өмнөх ба дараах үр дүнг харьцуулж оруул
python -m eval.evaluate --data data/real --split test --out reports/after_ft
python -m eval.evaluate --crops data/synth --limit 500   # зөвхөн томьёо таних хэсэг
python -m tests.layout_check --n 100                     # текст/томьёо ялгах нарийвчлал
```

**Анхаар:** test багцыг fine-tune-д огт бүү ашигла. Синтетик өгөгдлийг зөвхөн train-д нэм. NFR-05-ыг бодит зургийн test багц дээр хэмжинэ.

## Шалгасан байдал ба мэдэгдэж буй хязгаарлалт

- Layout алгоритмыг синтетик 180 зураг дээр (тэгшитгэл, бутархай, логарифм, язгуур, магадлал; 3 фонт, эргэлт, бүдгэрэлт, шуугиантай) туршихад томьёоны байрлалыг **97% зөв** (IoU>0.5) олсон. Нэг зургийн median хугацаа ~0.5 сек.
  Энэ туршилтыг `eng` загвар дээр англи тексттэй хийсэн, учир нь хөгжүүлэлтийн орчинд `mon`, pix2tex татах боломжгүй байсан. Монгол текст, pix2tex-тэй бүтэн үр дүнг `tests.layout_check` болон `eval.evaluate`-ээр өөрийн машин дээр хэмжинэ.
- Гараар бичсэн бодлого, геометрийн зураг, хүснэгт нь цар хүрээнд багтахгүй (7.2-ын дагуу).
- Олон мөрт систем тэгшитгэл (`\begin{cases}`) нь layout-д хэд хэдэн томьёо болж хуваагдаж магадгүй. Сурагч засварлах UI-аар нөхнө.
- Tesseract `ө/ү`-г `о/у` гэж андуурдаг. `ocr/text_post.py` дахь математикийн нэр томьёоны толиор засдаг тул энэ толийг админы нэр томьёоны сантай (FR-16) холбох нь зүйтэй.
