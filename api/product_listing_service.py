import os
import asyncio
import io
import json
from typing import Any


LANGUAGES = {
    "en": "English",
    "th": "Thai",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
}


class ProviderConfigurationError(ValueError):
    pass


class ProductListingService:
    def __init__(self) -> None:
        mock_mode = os.getenv("MOCK_AI_MODE", "true").lower() == "true"
        self.provider = "mock" if mock_mode else os.getenv("AI_PROVIDER", "mock").lower()
        self.external_ai_enabled = os.getenv("ENABLE_EXTERNAL_AI", "false").lower() == "true"
        self.api_key = os.getenv("GOOGLE_API_KEY", "")

        if self.provider not in {"mock", "gemini"}:
            raise ProviderConfigurationError(f"Unsupported AI_PROVIDER: {self.provider}")
        if self.provider == "gemini" and not self.external_ai_enabled:
            raise ProviderConfigurationError(
                "ENABLE_EXTERNAL_AI=true is required when AI_PROVIDER=gemini"
            )
        if self.provider == "gemini" and not self.api_key:
            raise ProviderConfigurationError(
                "GOOGLE_API_KEY is required when AI_PROVIDER=gemini"
            )

    async def analyze_product_image(
        self, image_data: bytes, language: str = "en"
    ) -> dict[str, Any]:
        if self.provider == "mock":
            return self._mock_listing(language)

        return await asyncio.to_thread(self._analyze_with_gemini, image_data, language)

    def _analyze_with_gemini(self, image_data: bytes, language: str) -> dict[str, Any]:
        try:
            import google.generativeai as genai
            from PIL import Image

            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            image.thumbnail((1024, 1024))
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content([self._prompt(language), image])
            listing = json.loads(response.text.removeprefix("```json").removesuffix("```").strip())
            return self._validate_external_listing(listing, language)
        except Exception as exc:
            raise RuntimeError(
                "Gemini analysis failed. Check provider configuration and try again."
            ) from exc

    @staticmethod
    def _prompt(language: str) -> str:
        language_name = LANGUAGES.get(language.lower(), language)
        return (
            "Describe only visible product attributes. Return JSON with title, description, "
            f"and 5-8 tags in {language_name}. Avoid unverified material, quality, performance, "
            "legal-compliance, and marketplace-approval claims."
        )

    @staticmethod
    def _validate_external_listing(listing: Any, language: str) -> dict[str, Any]:
        if not isinstance(listing, dict):
            raise ValueError("Provider response must be an object")
        if not all(isinstance(listing.get(field), str) and listing[field].strip() for field in ("title", "description")):
            raise ValueError("Provider response is missing title or description")
        if not isinstance(listing.get("tags"), list) or not all(
            isinstance(tag, str) and tag.strip() for tag in listing["tags"]
        ):
            raise ValueError("Provider response has invalid tags")

        return {
            "title": listing["title"].strip(),
            "description": listing["description"].strip(),
            "tags": [tag.strip() for tag in listing["tags"]],
            "language": LANGUAGES.get(language.lower(), language),
            "warnings": ["AI-generated draft; verify all claims before publishing."],
            "validation_status": "draft",
            "provider": "gemini",
            "provider_trace": "external-gemini; response_schema=validated",
        }

    @staticmethod
    def _mock_listing(language: str) -> dict[str, Any]:
        language_name = LANGUAGES.get(language.lower(), language)
        return {
            "title": "Minimalist Reusable Desk Organizer",
            "description": (
                "A compact organizer with a simple neutral finish for keeping small "
                "desk items together. This draft uses only synthetic fixture context; "
                "verify the material, dimensions, color, and intended use before publishing."
            ),
            "tags": ["desk organizer", "minimalist", "reusable", "workspace", "storage"],
            "language": language_name,
            "warnings": [
                "Synthetic demo output; visible product attributes were not inferred.",
                "Draft copy is not guaranteed to meet marketplace or legal requirements.",
            ],
            "validation_status": "draft",
            "provider": "mock",
            "provider_trace": "deterministic-local-v1; external_calls=0",
        }
