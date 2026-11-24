FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    OCR_BACKEND=cpu \
    OCR_VERSION=PP-OCRv6 \
    OCR_CPU_THREADS=2 \
    MAX_IMAGE_BYTES=10485760 \
    REQUEST_TIMEOUT_SECONDS=60 \
    ENABLE_LAYOUT=false \
    ENABLE_FORMULA=false \
    MODEL_DIR=/models \
    TMP_DIR=/tmp/ocr

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /models /tmp/ocr \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin ocr

COPY app.py .
COPY web/ ./web/

RUN chown -R 10001:10001 /app /models /tmp/ocr \
    && chmod -R 0755 /models

USER 10001
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
