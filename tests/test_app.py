import asyncio
import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from fastapi import HTTPException
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app import ocr


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


class OCRResponseTests(unittest.TestCase):
    def test_formats_numpy_detections_into_response_blocks(self):
        result = SimpleNamespace(
            boxes=np.array([[[1, 2], [9, 2], [9, 8], [1, 8]]]),
            txts=["recognized"],
            scores=[0.98765],
        )

        with patch("app.engine", return_value=result):
            response = asyncio.run(ocr(make_upload(make_png())))

        self.assertEqual(
            response["blocks"],
            [
                {
                    "order": 1,
                    "text": "recognized",
                    "bbox": [1, 2, 9, 8],
                    "confidence": 0.9877,
                }
            ],
        )

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


if __name__ == "__main__":
    unittest.main()
