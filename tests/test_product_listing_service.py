import os
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from product_listing_service import ProviderConfigurationError, ProductListingService


class ProductListingServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_mock_mode_is_deterministic_and_offline(self):
        settings = {
            "AI_PROVIDER": "mock",
            "MOCK_AI_MODE": "true",
            "ENABLE_EXTERNAL_AI": "false",
            "GOOGLE_API_KEY": "",
        }

        with patch.dict(os.environ, settings, clear=False):
            service = ProductListingService()
            first = await service.analyze_product_image(b"synthetic-image", "en")
            second = await service.analyze_product_image(b"different-bytes", "en")

        self.assertEqual(first, second)
        self.assertEqual(first["provider"], "mock")
        self.assertEqual(first["validation_status"], "draft")
        self.assertEqual(set(first), {
            "title", "description", "tags", "language", "warnings",
            "validation_status", "provider", "provider_trace",
        })

    def test_explicit_gemini_mode_requires_api_key(self):
        settings = {
            "AI_PROVIDER": "gemini",
            "MOCK_AI_MODE": "false",
            "ENABLE_EXTERNAL_AI": "true",
            "GOOGLE_API_KEY": "",
        }

        with patch.dict(os.environ, settings, clear=False):
            with self.assertRaisesRegex(
                ProviderConfigurationError,
                "GOOGLE_API_KEY is required when AI_PROVIDER=gemini",
            ):
                ProductListingService()

    def test_explicit_openrouter_mode_requires_api_key(self):
        settings = {
            "AI_PROVIDER": "openrouter",
            "MOCK_AI_MODE": "false",
            "ENABLE_EXTERNAL_AI": "true",
            "OPENROUTER_API_KEY": "",
        }

        with patch.dict(os.environ, settings, clear=False):
            with self.assertRaisesRegex(
                ProviderConfigurationError,
                "OPENROUTER_API_KEY is required when AI_PROVIDER=openrouter",
            ):
                ProductListingService()

    async def test_openrouter_mode_validates_openai_compatible_response(self):
        settings = {
            "AI_PROVIDER": "openrouter",
            "MOCK_AI_MODE": "false",
            "ENABLE_EXTERNAL_AI": "true",
            "OPENROUTER_API_KEY": "synthetic-openrouter-key",
            "OPENROUTER_MODEL": "google/gemma-4-26b-a4b-it:free",
        }
        response_body = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"title":"Synthetic organizer",'
                            '"description":"A demo organizer",'
                            '"tags":["desk","storage"]}'
                        )
                    }
                }
            ]
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return json.dumps(response_body).encode("utf-8")

        with patch.dict(os.environ, settings, clear=False):
            with patch(
                "product_listing_service.urllib.request.urlopen",
                return_value=FakeResponse(),
            ) as urlopen:
                result = await ProductListingService().analyze_product_image(
                    b"synthetic-image", "en", "image/png"
                )

        self.assertEqual(result["provider"], "openrouter")
        self.assertEqual(result["validation_status"], "draft")
        self.assertEqual(result["tags"], ["desk", "storage"])
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(
            urlopen.call_args.args[0].full_url,
            "https://openrouter.ai/api/v1/chat/completions",
        )
        request_body = json.loads(urlopen.call_args.args[0].data)
        self.assertTrue(
            request_body["messages"][0]["content"][1]["image_url"]["url"].startswith(
                "data:image/png;base64,"
            )
        )

    async def test_mock_mode_overrides_gemini_configuration(self):
        settings = {
            "AI_PROVIDER": "gemini",
            "MOCK_AI_MODE": "true",
            "ENABLE_EXTERNAL_AI": "true",
            "GOOGLE_API_KEY": "configured-but-unused",
        }

        with patch.dict(os.environ, settings, clear=False):
            result = await ProductListingService().analyze_product_image(b"low-quality", "th")

        self.assertEqual(result["provider"], "mock")
        self.assertEqual(result["language"], "Thai")
        self.assertTrue(result["warnings"])
        self.assertEqual(len(result["tags"]), 5)


if __name__ == "__main__":
    unittest.main()
