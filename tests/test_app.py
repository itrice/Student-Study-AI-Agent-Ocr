import asyncio
import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from fastapi import HTTPException
from PIL import Image
from starlette.datastructures import Headers, UploadFile
from starlette.requests import Request

from app import index_page, ocr, ocr_raw


def make_upload(data, content_type="image/png"):
    return UploadFile(
        file=BytesIO(data),
        filename="test.png",
        headers=Headers({"content-type": content_type}),
    )


def make_png():
    image = Image.new("RGB", (20, 10), "white")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def make_raw_request(data, content_type="image/png"):
    messages = iter(
        [{"type": "http.request", "body": data, "more_body": False}]
    )

    async def receive():
        return next(messages)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/ocr/raw",
        "headers": [(b"content-type", content_type.encode())],
    }
    return Request(scope, receive)


class OCRResponseTests(unittest.TestCase):
    def test_serves_ocr_upload_page(self):
        response = index_page()

        self.assertIn("题目 OCR 识别工作台", response.body.decode("utf-8"))
        self.assertIn("字符匹配率", response.body.decode("utf-8"))

    def test_formats_numpy_detections_into_response_blocks(self):
        result = SimpleNamespace(
            boxes=np.array([[[1, 2], [9, 2], [9, 8], [1, 8]]]),
            txts=["recognized"],
            scores=[0.98765],
        )
        writing_prediction = SimpleNamespace(label="printed", confidence=0.93)

        with (
            patch("app.engine", return_value=result),
            patch(
                "app.writing_classifier.predict",
                return_value=writing_prediction,
            ) as classify,
        ):
            response = asyncio.run(ocr(make_upload(make_png())))

        self.assertEqual(
            response["blocks"],
            [
                {
                    "order": 1,
                    "text": "recognized",
                    "bbox": [1, 2, 9, 8],
                    "confidence": 0.9877,
                    "writingType": "printed",
                    "writingTypeConfidence": 0.93,
                }
            ],
        )
        self.assertEqual(classify.call_args.args[0].size, (11, 10))
        self.assertEqual(
            classify.call_args.kwargs,
            {"return_details": True},
        )

    def test_marks_low_confidence_writing_type_unknown(self):
        result = SimpleNamespace(
            boxes=np.array([[[1, 2], [9, 2], [9, 8], [1, 8]]]),
            txts=["recognized"],
            scores=[0.9],
        )
        writing_prediction = SimpleNamespace(label="handwritten", confidence=0.55)

        with (
            patch("app.engine", return_value=result),
            patch(
                "app.writing_classifier.predict",
                return_value=writing_prediction,
            ),
        ):
            response = asyncio.run(ocr(make_upload(make_png())))

        self.assertEqual(response["blocks"][0]["writingType"], "unknown")
        self.assertEqual(response["blocks"][0]["writingTypeConfidence"], 0.55)

    def test_returns_empty_blocks_for_empty_numpy_results(self):
        result = SimpleNamespace(
            boxes=np.empty((0, 4, 2)),
            txts=np.empty((0,), dtype=str),
            scores=np.empty((0,)),
        )

        with patch("app.engine", return_value=result):
            response = asyncio.run(ocr(make_upload(make_png())))

        self.assertEqual(response["blocks"], [])

    def test_rejects_unsupported_media_type(self):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(ocr(make_upload(b"not an image", "application/octet-stream")))

        self.assertEqual(raised.exception.status_code, 415)

    def test_rejects_invalid_image_data(self):
        with patch("app.engine") as engine:
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(ocr(make_upload(b"not an image")))

        self.assertEqual(raised.exception.status_code, 400)
        engine.assert_not_called()

    def test_accepts_raw_image_bytes(self):
        result = SimpleNamespace(boxes=[], txts=[], scores=[])

        with patch("app.engine", return_value=result):
            response = asyncio.run(ocr_raw(make_raw_request(make_png())))

        self.assertEqual(response["blocks"], [])
        self.assertEqual(response["width"], 20)
        self.assertEqual(response["height"], 10)

    def test_rejects_oversized_raw_image(self):
        with patch("app.MAX_IMAGE_BYTES", 3):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(ocr_raw(make_raw_request(make_png())))

        self.assertEqual(raised.exception.status_code, 413)

    def test_rejects_unsupported_raw_media_type(self):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(
                ocr_raw(make_raw_request(b"data", "application/octet-stream"))
            )

        self.assertEqual(raised.exception.status_code, 415)


if __name__ == "__main__":
    unittest.main()
