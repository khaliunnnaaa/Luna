# ML сервис: ангилагч + BKT + (сонголттой) OCR. Torch ороогүй — OCR хэрэгтэй бол
# requirements-ocr.txt-г нэмж суулгасан image ашиглана (доорх тайлбарыг үз).
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-mon libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# OCR-той хувилбар (torch ~1 GB): --build-arg WITH_OCR=1
ARG WITH_OCR=0
# torch-ийн CPU хувилбарыг эхэлж суулгана (CUDA-тайгаас хэд дахин бага)
RUN if [ "$WITH_OCR" = "1" ]; then \
      pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
      pip install --no-cache-dir -r requirements-ocr.txt; \
    fi
COPY . .
EXPOSE 8001
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8001"]
