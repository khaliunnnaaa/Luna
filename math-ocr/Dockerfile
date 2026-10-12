FROM python:3.11-slim

# Tesseract + монгол хэлний загвар (Debian багцад tesseract-ocr-mon байдаг)
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-mon tesseract-ocr-eng libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# PyTorch-ийн CPU хувилбар (GPU-тэйгээс 5 дахин бага хэмжээтэй)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ocr ./ocr
COPY api.py .
# pix2tex-ийн жинг image дотор урьдчилан татна (сервер асахад хүлээхгүй)
RUN python -c "from pix2tex.cli import LatexOCR; LatexOCR()"

# Fine-tune хийсэн checkpoint байвал:  -e PIX2TEX_CHECKPOINT=/models/mn_math.pth -v ./models:/models
ENV OCR_BUDGET_S=5 OCR_WORKERS=2
EXPOSE 8001
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8001"]
