import os
import asyncio
import base64
import io
import json
import urllib.request
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
        self.api_key = ""
        self.model = ""

        if self.provider not in {"mock", "gemini", "openrouter"}:
            raise ProviderConfigurationError(f"Unsupported AI_PROVIDER: {self.provider}")
        if self.provider != "mock" and not self.external_ai_enabled:
            raise ProviderConfigurationError(
                f"ENABLE_EXTERNAL_AI=true is required when AI_PROVIDER={self.provider}"
            )
        if self.provider == "gemini":
            self.api_key = os.getenv("GOOGLE_API_KEY", "")
        elif self.provider == "openrouter":
            self.api_key = os.getenv("OPENROUTER_API_KEY", "")
            self.model = os.getenv(
                "OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it:free"
            )

        if self.provider != "mock" and not self.api_key:
            raise ProviderConfigurationError(
                f"{('GOOGLE_API_KEY' if self.provider == 'gemini' else 'OPENROUTER_API_KEY')} "
                f"is required when AI_PROVIDER={self.provider}"
            )

    async def analyze_product_image(
        self,
        image_data: bytes,
        language: str = "en",
        mime_type: str = "image/jpeg",
    ) -> dict[str, Any]:
        if self.provider == "mock":
            return self._mock_listing(language)

        if self.provider == "openrouter":
            return await asyncio.to_thread(
                self._analyze_with_openrouter, image_data, language, mime_type
            )

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
            listing = json.loads(self._strip_json_fence(response.text))
            return self._validate_external_listing(listing, language, "gemini")
        except Exception as exc:
            raise RuntimeError(
                "Gemini analysis failed. Check provider configuration and try again."
            ) from exc

    def _analyze_with_openrouter(
        self, image_data: bytes, language: str, mime_type: str
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._prompt(language)},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,"
                                + base64.b64encode(image_data).decode("ascii")
                            },
                        },
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": 300,
            "include_reasoning": False,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv(
                    "OPENROUTER_HTTP_REFERER",
                    "https://github.com/Praciller/AI-Product-Listing-Assistant",
                ),
                "X-Title": os.getenv(
                    "OPENROUTER_APP_NAME", "AI Product Listing Assistant"
                ),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "20")),
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content)
            listing = json.loads(self._strip_json_fence(content))
            return self._validate_external_listing(listing, language, "openrouter")
        except Exception as exc:
            raise RuntimeError(
                "OpenRouter analysis failed. Check provider configuration and try again."
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
    def _strip_json_fence(content: str) -> str:
        return content.removeprefix("```json").removesuffix("```").strip()

    @staticmethod
    def _validate_external_listing(
        listing: Any, language: str, provider: str
    ) -> dict[str, Any]:
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
            "provider": provider,
            "provider_trace": f"external-{provider}; response_schema=validated",
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
