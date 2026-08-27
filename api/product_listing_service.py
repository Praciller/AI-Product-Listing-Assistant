import os
import asyncio
from typing import Annotated, Any, Awaitable, Callable, Literal

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)

from provider_resilience import (
    ExternalInferenceClient,
    ProcessLocalCircuitBreaker,
    ProviderHTTPError,
    ProviderOutputError,
    ProviderTelemetry,
    ProviderTransportError,
    ResilienceConfig,
    classify_http_status,
    default_jitter,
    parse_json_text,
    retry_delay,
)


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

MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 4000
MAX_TAG_LENGTH = 50


class ListingContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    description: str = Field(min_length=1, max_length=MAX_DESCRIPTION_LENGTH)
    tags: list[str] = Field(min_length=5, max_length=8)

    @field_validator("title", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: Any) -> Any:
        if not isinstance(value, list):
            raise ValueError("tags must be a list")

        tags = []
        seen = set()
        for tag in value:
            if not isinstance(tag, str):
                raise ValueError("tags must contain only strings")
            normalized = " ".join(tag.split())
            if not normalized:
                raise ValueError("tags must not be empty")
            if len(normalized) > MAX_TAG_LENGTH:
                raise ValueError("tag exceeds maximum length")
            key = normalized.casefold()
            if key not in seen:
                seen.add(key)
                tags.append(normalized)
        return tags


class ProviderListingPayload(ListingContent):
    pass


class ProductListing(ListingContent):
    language: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
    ]
    warnings: list[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
        ]
    ] = Field(min_length=1, max_length=5)
    validation_status: Literal["draft"]
    provider: Literal["mock", "external"]
    provider_trace: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]


class ProviderConfigurationError(ValueError):
    pass


class ProviderExecutionError(RuntimeError):
    def __init__(
        self,
        message: str = "External AI analysis failed. Please try again.",
        *,
        telemetry: ProviderTelemetry | None = None,
    ) -> None:
        self.telemetry = telemetry
        super().__init__(message)


class ProductListingService:
    def __init__(
        self,
        *,
        http_transport: httpx.AsyncBaseTransport | None = None,
        circuit_breaker: ProcessLocalCircuitBreaker | None = None,
        sleeper: Callable[[float], Awaitable[None]] | None = None,
        jitter: Callable[[float], float] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        mock_mode = os.getenv("MOCK_AI_MODE", "true").lower() == "true"
        self.provider = (
            "mock" if mock_mode else os.getenv("AI_PROVIDER", "mock").lower()
        )
        self.external_ai_enabled = (
            os.getenv("ENABLE_EXTERNAL_AI", "false").lower() == "true"
        )
        self.api_key = os.getenv("EXTERNAL_AI_API_KEY", "")
        self.endpoint = os.getenv("EXTERNAL_AI_ENDPOINT", "")
        self.model = os.getenv("EXTERNAL_AI_MODEL", "")

        if self.provider not in {"mock", "external"}:
            raise ProviderConfigurationError(
                f"Unsupported AI_PROVIDER: {self.provider}"
            )
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
            try:
                self.resilience_config = ResilienceConfig.from_environment()
            except ValueError as exc:
                raise ProviderConfigurationError(str(exc)) from exc
            self.timeout_seconds = self.resilience_config.read_timeout_seconds
            self.max_retries = self.resilience_config.max_retries
            self.retry_backoff_seconds = self.resilience_config.retry_backoff_seconds
            self._circuit_breaker = circuit_breaker or ProcessLocalCircuitBreaker(
                failure_threshold=self.resilience_config.circuit_failure_threshold,
                cooldown_seconds=self.resilience_config.circuit_cooldown_seconds,
                clock=clock,
            )
            self._sleeper = sleeper or asyncio.sleep
            self._jitter = jitter or default_jitter
            self._external_client = ExternalInferenceClient(
                self.endpoint,
                self.api_key,
                self.model,
                self.resilience_config,
                transport=http_transport,
            )

    async def analyze_product_image(
        self,
        image_data: bytes,
        language: str = "en",
        mime_type: str = "image/jpeg",
    ) -> ProductListing:
        if self.provider == "mock":
            return self._mock_listing(language)

        if not self._circuit_breaker.before_request():
            telemetry = self._telemetry(
                attempts=0,
                failure_category="circuit_open",
                degraded=True,
            )
            raise ProviderExecutionError(telemetry=telemetry)

        attempts = 0
        try:
            async with asyncio.timeout(
                self.resilience_config.request_timeout_seconds
            ):
                while attempts < self.resilience_config.max_attempts:
                    attempts += 1
                    try:
                        response_text = await self._analyze_with_external(
                            image_data, language, mime_type
                        )
                        listing = self._validate_external_listing(
                            parse_json_text(response_text), language
                        )
                    except ProviderHTTPError as exc:
                        transient, failure_category = classify_http_status(
                            exc.status_code
                        )
                    except ProviderTransportError as exc:
                        transient = True
                        failure_category = exc.category
                    except ProviderOutputError:
                        transient = False
                        failure_category = "output_validation"
                    except (TimeoutError, ConnectionError, httpx.TimeoutException):
                        transient = True
                        failure_category = "timeout"
                    except httpx.TransportError:
                        transient = True
                        failure_category = "network"
                    except ValidationError:
                        transient = False
                        failure_category = "output_validation"
                    except Exception:
                        transient = False
                        failure_category = "provider_error"
                    else:
                        self._circuit_breaker.record_success()
                        telemetry = self._telemetry(attempts=attempts)
                        return listing.model_copy(
                            update={
                                "provider_trace": telemetry.trace(
                                    "response_schema=validated"
                                )
                            }
                        )

                    if not transient:
                        self._circuit_breaker.record_non_transient_failure()
                        telemetry = self._telemetry(
                            attempts=attempts,
                            failure_category=failure_category,
                            degraded=True,
                        )
                        raise ProviderExecutionError(telemetry=telemetry)

                    if attempts >= self.resilience_config.max_attempts:
                        self._circuit_breaker.record_transient_failure()
                        telemetry = self._telemetry(
                            attempts=attempts,
                            failure_category=failure_category,
                            degraded=True,
                        )
                        raise ProviderExecutionError(telemetry=telemetry)

                    await self._sleeper(
                        retry_delay(
                            attempts - 1,
                            self.resilience_config,
                            jitter=self._jitter,
                        )
                    )
        except asyncio.TimeoutError as exc:
            self._circuit_breaker.record_transient_failure()
            telemetry = self._telemetry(
                attempts=attempts,
                failure_category="overall_timeout",
                degraded=True,
            )
            raise ProviderExecutionError(telemetry=telemetry) from exc

        raise AssertionError("unreachable")

    async def _analyze_with_external(
        self, image_data: bytes, language: str, mime_type: str
    ) -> str:
        return await self._external_client.generate_content(
            image_data, self._prompt(language), mime_type
        )

    def _telemetry(
        self,
        *,
        attempts: int,
        failure_category: str = "none",
        degraded: bool = False,
    ) -> ProviderTelemetry:
        return ProviderTelemetry(
            route=self.provider,
            attempts=attempts,
            retry_count=max(0, attempts - 1),
            failure_category=failure_category,
            fallback="none",
            degraded=degraded,
            circuit_state=self._circuit_breaker.state,
        )

    @staticmethod
    def _prompt(language: str) -> str:
        language_name = LANGUAGES.get(language.lower(), language)
        return (
            "Describe only visible product attributes. Return JSON with title, description, "
            f"and 5-8 tags in {language_name}. Avoid unverified material, quality, performance, "
            "legal-compliance, and marketplace-approval claims."
        )

    @staticmethod
    def _validate_external_listing(listing: Any, language: str) -> ProductListing:
        try:
            payload = ProviderListingPayload.model_validate(listing)
            return ProductListing(
                title=payload.title,
                description=payload.description,
                tags=payload.tags,
                language=LANGUAGES.get(language.lower(), language),
                warnings=["AI-generated draft; verify all claims before publishing."],
                validation_status="draft",
                provider="external",
                provider_trace="route=external; response_schema=validated",
            )
        except ValidationError as exc:
            raise ProviderOutputError("provider output failed schema validation") from exc

    @staticmethod
    def _mock_listing(language: str) -> ProductListing:
        language_name = LANGUAGES.get(language.lower(), language)
        return ProductListing(
            title="Minimalist Reusable Desk Organizer",
            description=(
                "A compact organizer with a simple neutral finish for keeping small "
                "desk items together. This draft uses only synthetic fixture context; "
                "verify the material, dimensions, color, and intended use before publishing."
            ),
            tags=["desk organizer", "minimalist", "reusable", "workspace", "storage"],
            language=language_name,
            warnings=[
                "Synthetic demo output; visible product attributes were not inferred.",
                "Draft copy is not guaranteed to meet marketplace or legal requirements.",
            ],
            validation_status="draft",
            provider="mock",
            provider_trace="deterministic-local-v1; external_calls=0",
        )
