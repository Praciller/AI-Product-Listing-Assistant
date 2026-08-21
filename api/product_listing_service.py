import asyncio
import base64
import json
import os
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
    """Mock-first product listing service with an optional generic external endpoint."""

    def __init__(self) -> None:
        mock_mode = os.getenv("MOCK_AI_MODE", "true").lower() == "true"
        self.provider = "mock" if mock_mode else os.getenv("AI_PROVIDER", "mock").lower()
        self.external_ai_enabled = os.getenv("ENABLE_EXTERNAL_AI", "false").lower() == "true"
        self.api_key = os.getenv("EXTERNAL_AI_API_KEY", "")
        self.endpoint = os.getenv("EXTERNAL_AI_ENDPOINT", "")
        self.model = os.getenv("EXTERNAL_AI_MODEL", "")

        if self.provider not in {"mock", "external"}:
            raise ProviderConfigurationError(f"Unsupported AI_PROVIDER: {self.provider}")
        if self.provider == "external" and not self.external_ai_enabled:
            raise ProviderConfigurationError(
                "ENABLE_EXTERNAL_AI=true is required when AI_PROVIDER=external"
            )
        if self.provider == "external":
            missing = [
                name
                for name, value in (
                    ("EXTERNAL_AI_ENDPOINT", self.endpoint),
                    ("EXTERNAL_AI_API_KEY", self.api_key),
                    ("EXTERNAL_AI_MODEL", self.model),
                )
                if not value
            ]
            if missing:
                raise ProviderConfigurationError(
                    f"Missing external inference configuration: {', '.join(missing)}"
                )

    async def analyze_product_image(
        self,
        image_data: bytes,
        language: str = "en",
        mime_type: str = "image/jpeg",
    ) -> dict[str, Any]:
        if self.provider == "mock":
            return self._mock_listing(language)

        return await asyncio.to_thread(
            self._analyze_with_external_endpoint, image_data, language, mime_type
        )

    def _analyze_with_external_endpoint(
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
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=float(os.getenv("EXTERNAL_AI_TIMEOUT_SECONDS", "20")),
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content)
            listing = json.loads(self._strip_json_fence(content))
            return self._validate_external_listing(listing, language)
        except Exception as exc:
            raise RuntimeError(
                "External analysis failed. Check endpoint configuration and try again."
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
    def _validate_external_listing(listing: Any, language: str) -> dict[str, Any]:
        if not isinstance(listing, dict):
            raise ValueError("External response must be an object")
        if not all(
            isinstance(listing.get(field), str) and listing[field].strip()
            for field in ("title", "description")
        ):
            raise ValueError("External response is missing title or description")
        if not isinstance(listing.get("tags"), list) or not all(
            isinstance(tag, str) and tag.strip() for tag in listing["tags"]
        ):
            raise ValueError("External response has invalid tags")

        return {
            "title": listing["title"].strip(),
            "description": listing["description"].strip(),
            "tags": [tag.strip() for tag in listing["tags"]],
            "language": LANGUAGES.get(language.lower(), language),
            "warnings": ["Generated draft; verify all claims before publishing."],
            "validation_status": "draft",
            "provider": "external",
            "provider_trace": "external-endpoint; response_schema=validated",
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
