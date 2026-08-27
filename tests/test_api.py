import io
import struct
import sys
import unittest
import zlib
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from main import app, parse_cors_origins


class UploadValidationTests(unittest.TestCase):
    client = TestClient(app)

    @staticmethod
    def image_bytes(image_format="PNG", size=(8, 8)):
        output = io.BytesIO()
        Image.new("RGB", size, "white").save(output, format=image_format)
        return output.getvalue()

    @classmethod
    def png_with_declared_dimensions(cls, width, height):
        data = bytearray(cls.image_bytes(size=(1, 1)))
        data[16:24] = struct.pack(">II", width, height)
        data[29:33] = struct.pack(">I", zlib.crc32(data[12:29]))
        return bytes(data)

    def test_oversized_upload_is_rejected(self):
        response = self.client.post(
            "/generate-product-info",
            files={"file": ("large.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
            data={"language": "en"},
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            response.json(),
            {
                "success": False,
                "error": "Image exceeds the 5 MiB upload limit.",
            },
        )

    def test_invalid_image_bytes_are_rejected(self):
        response = self.client.post(
            "/generate-product-info",
            files={"file": ("fake.png", b"not-an-image", "image/png")},
            data={"language": "en"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "success": False,
                "error": "Image content is corrupt or does not match its declared format.",
            },
        )

    def test_fake_mime_type_is_rejected(self):
        response = self.client.post(
            "/generate-product-info",
            files={"file": ("image.png", self.image_bytes(), "text/plain")},
            data={"language": "en"},
        )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(
            response.json(),
            {
                "success": False,
                "error": "Only JPEG, PNG, and WebP images are supported.",
            },
        )

    def test_corrupt_image_with_valid_signature_is_rejected(self):
        response = self.client.post(
            "/generate-product-info",
            files={
                "file": (
                    "corrupt.png",
                    b"\x89PNG\r\n\x1a\nnot-a-decodable-png",
                    "image/png",
                )
            },
            data={"language": "en"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "success": False,
                "error": "Image content is corrupt or does not match its declared format.",
            },
        )

    def test_excessive_pixel_dimensions_are_rejected_before_decode(self):
        response = self.client.post(
            "/generate-product-info",
            files={
                "file": (
                    "huge.png",
                    self.png_with_declared_dimensions(6000, 6000),
                    "image/png",
                )
            },
            data={"language": "en"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "success": False,
                "error": "Image dimensions exceed the configured pixel limit.",
            },
        )

    def test_unsupported_image_format_is_rejected(self):
        response = self.client.post(
            "/generate-product-info",
            files={"file": ("image.gif", self.image_bytes("GIF"), "image/gif")},
            data={"language": "en"},
        )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(
            response.json()["error"], "Only JPEG, PNG, and WebP images are supported."
        )

    def test_empty_upload_is_rejected(self):
        response = self.client.post(
            "/generate-product-info",
            files={"file": ("empty.png", b"", "image/png")},
            data={"language": "en"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "Empty file uploaded. Please select a valid image.",
        )

    def test_supported_signature_must_match_declared_media_type(self):
        response = self.client.post(
            "/generate-product-info",
            files={"file": ("image.jpg", self.image_bytes(), "image/jpeg")},
            data={"language": "en"},
        )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(
            response.json()["error"],
            "Image signature does not match its declared media type.",
        )

    def test_valid_synthetic_supported_images_are_accepted(self):
        fixtures = (
            ("JPEG", "image/jpeg", "image.jpg"),
            ("PNG", "image/png", "image.png"),
            ("WEBP", "image/webp", "image.webp"),
        )

        for image_format, media_type, filename in fixtures:
            with self.subTest(image_format=image_format):
                response = self.client.post(
                    "/generate-product-info",
                    files={
                        "file": (
                            filename,
                            self.image_bytes(image_format),
                            media_type,
                        )
                    },
                    data={"language": "en"},
                )

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertTrue(payload["success"])
                self.assertEqual(payload["data"]["provider"], "mock")
                self.assertEqual(len(payload["data"]["tags"]), 5)

    def test_provider_errors_do_not_leak_internal_details(self):
        internal_error = RuntimeError(
            r"provider failed with key=secret-value at C:\private\image.png"
        )
        with patch(
            "main.product_listing_service.analyze_product_image",
            new=AsyncMock(side_effect=internal_error),
        ):
            response = self.client.post(
                "/generate-product-info",
                files={"file": ("image.png", self.image_bytes(), "image/png")},
                data={"language": "en"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "success": False,
                "error": "Analysis failed. Check provider configuration and try again.",
            },
        )
        self.assertNotIn("secret-value", response.text)
        self.assertNotIn("private", response.text)


class CorsConfigurationTests(unittest.TestCase):
    def test_cors_origins_are_parsed_normalized_and_deduplicated(self):
        self.assertEqual(
            parse_cors_origins(None),
            [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ],
        )
        self.assertEqual(
            parse_cors_origins(
                " https://shop.example.com/, http://localhost:3001, https://shop.example.com "
            ),
            ["https://shop.example.com", "http://localhost:3001"],
        )
        with self.assertRaisesRegex(ValueError, "CORS_ORIGINS"):
            parse_cors_origins("*")

        cors = app.user_middleware[0].kwargs
        self.assertEqual(
            cors["allow_origins"],
            [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ],
        )
        self.assertFalse(cors["allow_credentials"])
        self.assertEqual(cors["allow_methods"], ["POST"])
        self.assertEqual(cors["allow_headers"], ["Content-Type"])


if __name__ == "__main__":
    unittest.main()
