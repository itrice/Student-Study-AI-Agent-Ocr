import io
import os
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from PIL import Image, UnidentifiedImageError
from rapidocr import RapidOCR


MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", "10485760"))
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
PAGE_PATH = Path(__file__).parent / "web" / "index.html"

app = FastAPI(title="Internal OCR Service", docs_url=None, redoc_url=None)
engine = RapidOCR()


@app.get("/", response_class=HTMLResponse)
def index_page():
    return HTMLResponse(PAGE_PATH.read_text(encoding="utf-8"))


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    return {
        "status": "ready",
        "modelVersion": "PP-OCRv6-small",
    }


@app.get("/version")
def version():
    return {
        "engine": "rapidocr",
        "modelVersion": "PP-OCRv6-small",
        "ocrBackend": "cpu",
    }


@app.post("/v1/ocr")
async def ocr(image: UploadFile = File(...)):
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail={"code": "UNSUPPORTED_IMAGE_TYPE", "message": "Unsupported image type"},
        )

    data = await image.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"code": "IMAGE_TOO_LARGE", "message": "Image exceeds size limit"},
        )

    return recognize_image(data)


@app.post("/v1/ocr/raw")
async def ocr_raw(request: Request):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail={"code": "UNSUPPORTED_IMAGE_TYPE", "message": "Unsupported image type"},
        )

    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail={"code": "IMAGE_TOO_LARGE", "message": "Image exceeds size limit"},
            )

    return recognize_image(bytes(data))


def recognize_image(data: bytes):
    started = time.monotonic()
    try:
        pil_image = Image.open(io.BytesIO(data))
        pil_image.load()
        pil_image = pil_image.convert("RGB")
        width, height = pil_image.size
        result = engine(pil_image)
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_IMAGE", "message": "Unable to decode image"},
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"code": "OCR_PROCESSING_FAILED", "message": "OCR processing failed"},
        )

    blocks = []
    boxes = getattr(result, "boxes", None)
    texts = getattr(result, "txts", None)
    scores = getattr(result, "scores", None)

    if boxes is None:
        boxes = []
    if texts is None:
        texts = []
    if scores is None:
        scores = []

    for index, (box, text, confidence) in enumerate(zip(boxes, texts, scores), start=1):
        if not text:
            continue
        points = [int(value) for point in box for value in point]
        left = min(points[0::2])
        top = min(points[1::2])
        right = max(points[0::2])
        bottom = max(points[1::2])
        blocks.append(
            {
                "order": index,
                "text": text,
                "bbox": [left, top, right, bottom],
                "confidence": round(float(confidence), 4),
            }
        )

    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    return {
        "engine": "rapidocr",
        "modelVersion": "PP-OCRv6-small",
        "width": width,
        "height": height,
        "processingTimeMs": elapsed_ms,
        "blocks": blocks,
    }
