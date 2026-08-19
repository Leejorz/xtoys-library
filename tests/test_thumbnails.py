import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from core.thumbnails import ThumbnailExtractor


class _Headers:
    def get(self, key, default=None):
        if key == "Content-Type":
            return "image/png"
        return default


class _Response:
    headers = _Headers()

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, _limit):
        return self.payload


class ThumbnailTests(unittest.TestCase):
    def test_download_image_writes_original_xtoys_data_url_format(self):
        source = io.BytesIO()
        Image.new("RGB", (640, 360), (20, 40, 60)).save(source, format="PNG")
        payload = source.getvalue()

        with tempfile.TemporaryDirectory() as directory:
            stem = Path(directory) / "example-thumbnail"
            with patch(
                "core.thumbnails.urlopen",
                return_value=_Response(payload),
            ):
                output = ThumbnailExtractor.download_image(
                    "https://example.com/preview.png",
                    stem,
                )

            self.assertIsNotNone(output)
            self.assertEqual(output.suffix, ".jpeg")

            data_url = output.read_text(encoding="utf-8")
            self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))

            jpeg = base64.b64decode(data_url.split(",", 1)[1])
            with Image.open(io.BytesIO(jpeg)) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.mode, "RGB")
                self.assertLessEqual(max(image.size), 256)


if __name__ == "__main__":
    unittest.main()
