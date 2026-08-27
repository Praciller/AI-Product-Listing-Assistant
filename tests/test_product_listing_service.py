import asyncio
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from PIL import Image
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from product_listing_service import (
    ProductListing,
    ProcessLocalCircuitBreaker,
    ProviderConfigurationError,
    ProviderExecutionError,
    ProductListingService,
)


def synthetic_png():
    output = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(output, format="PNG")
    return output.getvalue()


def valid_provider_response():
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "title": "Desk organizer",
                                "description": "Synthetic draft",
                                "tags": [
                                    "desk",
                                    "storage",
                                    "workspace",
                                    "minimalist",
                                    "reusable",
                                ],
                            }
                        )
                    }
                }
            ]
        },
    )


def external_settings(**overrides):
    settings = {
        "AI_PROVIDER": "external",
        "MOCK_AI_MODE": "false",
        "ENABLE_EXTERNAL_AI": "true",
        "EXTERNAL_AI_ENDPOINT": "https://inference.example.test/v1/messages",
        "EXTERNAL_AI_API_KEY": "configured-test-key",
        "EXTERNAL_AI_MODEL": "vision-model",
        "EXTERNAL_AI_CONNECT_TIMEOUT_SECONDS": "1",
        "EXTERNAL_AI_READ_TIMEOUT_SECONDS": "1",
        "EXTERNAL_AI_REQUEST_TIMEOUT_SECONDS": "5",
        "EXTERNAL_AI_MAX_RETRIES": "1",
        "EXTERNAL_AI_RETRY_BACKOFF_SECONDS": "0.25",
        "EXTERNAL_AI_RETRY_MAX_BACKOFF_SECONDS": "1",
        "EXTERNAL_AI_RETRY_JITTER_SECONDS": "0",
        "EXTERNAL_AI_CIRCUIT_FAILURE_THRESHOLD": "3",
        "EXTERNAL_AI_CIRCUIT_COOLDOWN_SECONDS": "10",
    }
    settings.update(overrides)
    return settings


def sequence_transport(outcomes, requests):
    remaining = list(outcomes)

    def handler(request):
        requests.append(request)
        outcome = remaining.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return httpx.MockTransport(handler)


class ProductListingContractTests(unittest.TestCase):
    def test_tags_are_normalized_and_deduplicated(self):
        listing = ProductListing(
            title="  Desk organizer  ",
            description="  A synthetic listing draft.  ",
            tags=[
                " desk   organizer ",
                "Desk Organizer",
                "storage",
                "workspace",
                "minimalist",
                "reusable",
                "organization",
            ],
            language="English",
            warnings=["Review before publishing."],
            validation_status="draft",
            provider="external",
            provider_trace="route=external; response_schema=validated",
        )

        self.assertEqual(listing.title, "Desk organizer")
        self.assertEqual(listing.description, "A synthetic listing draft.")
        self.assertEqual(
            listing.tags,
            [
                "desk organizer",
                "storage",
                "workspace",
                "minimalist",
                "reusable",
                "organization",
            ],
        )

    def test_invalid_tag_count_is_rejected_after_deduplication(self):
        common = {
            "title": "Desk organizer",
            "description": "A synthetic listing draft.",
            "language": "English",
            "warnings": ["Review before publishing."],
            "validation_status": "draft",
            "provider": "external",
            "provider_trace": "route=external; response_schema=validated",
        }

        with self.assertRaises(ValidationError):
            ProductListing(tags=["one", "two", "three", "four"], **common)
        with self.assertRaises(ValidationError):
            ProductListing(tags=["one", "two", "three", "four", "ONE"], **common)

    def test_text_and_tag_lengths_are_bounded(self):
        common = {
            "description": "A synthetic listing draft.",
            "tags": ["one", "two", "three", "four", "five"],
            "language": "English",
            "warnings": ["Review before publishing."],
            "validation_status": "draft",
            "provider": "external",
            "provider_trace": "route=external; response_schema=validated",
        }
        with self.assertRaises(ValidationError):
            ProductListing(title="x" * 201, **common)
        with self.assertRaises(ValidationError):
            ProductListing(
                title="Desk organizer",
                **{**common, "tags": ["x" * 51, "two", "three", "four", "five"]},
            )


class ProductListingServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_mock_mode_is_deterministic_and_offline(self):
        settings = {
            "AI_PROVIDER": "mock",
            "MOCK_AI_MODE": "true",
            "ENABLE_EXTERNAL_AI": "false",
            "EXTERNAL_AI_API_KEY": "",
        }

        with patch.dict(os.environ, settings, clear=False):
            service = ProductListingService()
            first = await service.analyze_product_image(b"synthetic-image", "en")
            second = await service.analyze_product_image(b"different-bytes", "en")

        self.assertIsInstance(first, ProductListing)
        self.assertEqual(first, second)
        self.assertEqual(first.provider, "mock")
        self.assertEqual(first.validation_status, "draft")
        self.assertEqual(
            set(first.model_dump()),
            {
                "title",
                "description",
                "tags",
                "language",
                "warnings",
                "validation_status",
                "provider",
                "provider_trace",
            },
        )

    def test_explicit_external_mode_requires_complete_configuration(self):
        settings = {
            "AI_PROVIDER": "external",
            "MOCK_AI_MODE": "false",
            "ENABLE_EXTERNAL_AI": "true",
            "EXTERNAL_AI_ENDPOINT": "https://inference.example.test/v1/messages",
            "EXTERNAL_AI_API_KEY": "",
            "EXTERNAL_AI_MODEL": "vision-model",
        }

        with patch.dict(os.environ, settings, clear=False):
            with self.assertRaisesRegex(
                ProviderConfigurationError,
                "Missing external inference configuration: EXTERNAL_AI_API_KEY",
            ):
                ProductListingService()

    async def test_mock_mode_overrides_external_configuration(self):
        settings = {
            "AI_PROVIDER": "external",
            "MOCK_AI_MODE": "true",
            "ENABLE_EXTERNAL_AI": "true",
            "EXTERNAL_AI_ENDPOINT": "https://inference.example.test/v1/messages",
            "EXTERNAL_AI_API_KEY": "configured-but-unused",
            "EXTERNAL_AI_MODEL": "vision-model",
        }

        with patch.dict(os.environ, settings, clear=False):
            result = await ProductListingService().analyze_product_image(
                b"low-quality", "th"
            )

        self.assertEqual(result.provider, "mock")
        self.assertEqual(result.language, "Thai")
        self.assertTrue(result.warnings)
        self.assertEqual(len(result.tags), 5)

    async def test_mock_mode_makes_zero_external_calls(self):
        settings = {
            "AI_PROVIDER": "external",
            "MOCK_AI_MODE": "true",
            "ENABLE_EXTERNAL_AI": "true",
            "EXTERNAL_AI_ENDPOINT": "https://inference.example.test/v1/messages",
            "EXTERNAL_AI_API_KEY": "configured-but-unused",
            "EXTERNAL_AI_MODEL": "vision-model",
        }
        requests = []
        transport = sequence_transport([valid_provider_response()], requests)

        with patch.dict(os.environ, settings, clear=False):
            await ProductListingService(
                http_transport=transport
            ).analyze_product_image(synthetic_png(), "en")

        self.assertEqual(requests, [])

    async def test_first_attempt_success_has_safe_telemetry(self):
        requests = []
        transport = sequence_transport([valid_provider_response()], requests)
        sleeper = AsyncMock()

        with patch.dict(os.environ, external_settings(), clear=False):
            service = ProductListingService(
                http_transport=transport,
                sleeper=sleeper,
                jitter=lambda maximum: 0.0,
            )
            listing = await service.analyze_product_image(synthetic_png(), "en")

        self.assertEqual(len(requests), 1)
        self.assertEqual(listing.provider, "external")
        self.assertIn("attempts=1", listing.provider_trace)
        self.assertIn("retries=0", listing.provider_trace)
        self.assertIn("failure=none", listing.provider_trace)
        self.assertIn("fallback=none", listing.provider_trace)
        self.assertIn("degraded=false", listing.provider_trace)
        self.assertIn("circuit=CLOSED", listing.provider_trace)
        self.assertNotIn("configured-test-key", listing.provider_trace)
        self.assertEqual(requests[0].headers["authorization"], "Bearer configured-test-key")
        sleeper.assert_not_awaited()

    async def test_timeout_then_success_retries_once_without_real_sleep(self):
        requests = []
        transport = sequence_transport(
            [httpx.ReadTimeout("simulated read timeout"), valid_provider_response()],
            requests,
        )
        sleeper = AsyncMock()

        with patch.dict(os.environ, external_settings(), clear=False):
            service = ProductListingService(
                http_transport=transport,
                sleeper=sleeper,
                jitter=lambda maximum: 0.0,
            )
            listing = await service.analyze_product_image(synthetic_png(), "en")

        self.assertEqual(len(requests), 2)
        self.assertIn("attempts=2", listing.provider_trace)
        self.assertIn("retries=1", listing.provider_trace)
        sleeper.assert_awaited_once_with(0.25)

    async def test_overall_timeout_is_bounded_and_does_not_start_another_attempt(self):
        requests = []

        async def slow_handler(request):
            requests.append(request)
            await asyncio.sleep(0.05)
            return valid_provider_response()

        transport = httpx.MockTransport(slow_handler)
        sleeper = AsyncMock()

        with patch.dict(
            os.environ,
            external_settings(
                EXTERNAL_AI_REQUEST_TIMEOUT_SECONDS="0.01", EXTERNAL_AI_MAX_RETRIES="3"
            ),
            clear=False,
        ):
            service = ProductListingService(
                http_transport=transport, sleeper=sleeper, jitter=lambda maximum: 0.0
            )
            with self.assertRaises(ProviderExecutionError) as raised:
                await service.analyze_product_image(synthetic_png(), "en")

        self.assertEqual(len(requests), 1)
        self.assertEqual(raised.exception.telemetry.failure_category, "overall_timeout")
        self.assertEqual(raised.exception.telemetry.attempts, 1)
        sleeper.assert_not_awaited()

    async def test_429_then_success_retries_once(self):
        requests = []
        transport = sequence_transport(
            [httpx.Response(429), valid_provider_response()], requests
        )

        with patch.dict(os.environ, external_settings(), clear=False):
            service = ProductListingService(
                http_transport=transport,
                sleeper=AsyncMock(),
                jitter=lambda maximum: 0.0,
            )
            listing = await service.analyze_product_image(synthetic_png(), "en")

        self.assertEqual(len(requests), 2)
        self.assertIn("attempts=2", listing.provider_trace)

    async def test_500_then_success_retries_once(self):
        requests = []
        transport = sequence_transport(
            [httpx.Response(500), valid_provider_response()], requests
        )

        with patch.dict(os.environ, external_settings(), clear=False):
            service = ProductListingService(
                http_transport=transport,
                sleeper=AsyncMock(),
                jitter=lambda maximum: 0.0,
            )
            listing = await service.analyze_product_image(synthetic_png(), "en")

        self.assertEqual(len(requests), 2)
        self.assertEqual(listing.tags, ["desk", "storage", "workspace", "minimalist", "reusable"])

    async def test_retry_exhaustion_reports_exact_attempts_and_opens_budget_at_threshold(self):
        requests = []
        transport = sequence_transport(
            [
                httpx.ConnectError("simulated connection reset"),
                httpx.ConnectError("simulated connection reset"),
                httpx.ConnectError("simulated connection reset"),
            ],
            requests,
        )
        sleeper = AsyncMock()

        with patch.dict(
            os.environ,
            external_settings(
                EXTERNAL_AI_MAX_RETRIES="2", EXTERNAL_AI_CIRCUIT_FAILURE_THRESHOLD="1"
            ),
            clear=False,
        ):
            service = ProductListingService(
                http_transport=transport,
                sleeper=sleeper,
                jitter=lambda maximum: 0.0,
            )
            with self.assertRaises(ProviderExecutionError) as raised:
                await service.analyze_product_image(synthetic_png(), "en")

        self.assertEqual(len(requests), 3)
        self.assertEqual(raised.exception.telemetry.attempts, 3)
        self.assertEqual(raised.exception.telemetry.retry_count, 2)
        self.assertEqual(raised.exception.telemetry.failure_category, "network")
        self.assertEqual(raised.exception.telemetry.circuit_state.value, "OPEN")
        self.assertEqual(sleeper.await_count, 2)

    async def test_400_is_not_retried_or_counted_as_provider_health_failure(self):
        requests = []
        transport = sequence_transport([httpx.Response(400)], requests)

        with patch.dict(os.environ, external_settings(EXTERNAL_AI_MAX_RETRIES="3"), clear=False):
            service = ProductListingService(
                http_transport=transport, sleeper=AsyncMock(), jitter=lambda maximum: 0.0
            )
            with self.assertRaises(ProviderExecutionError) as raised:
                await service.analyze_product_image(synthetic_png(), "en")

        self.assertEqual(len(requests), 1)
        self.assertEqual(raised.exception.telemetry.failure_category, "http_4xx")
        self.assertEqual(raised.exception.telemetry.circuit_state.value, "CLOSED")
        self.assertNotIn("configured-test-key", str(raised.exception))
        self.assertNotIn("generativelanguage", str(raised.exception))

    async def test_401_and_403_are_not_retried(self):
        for status_code in (401, 403):
            with self.subTest(status_code=status_code):
                requests = []
                transport = sequence_transport([httpx.Response(status_code)], requests)
                with patch.dict(os.environ, external_settings(EXTERNAL_AI_MAX_RETRIES="3"), clear=False):
                    service = ProductListingService(
                        http_transport=transport,
                        sleeper=AsyncMock(),
                        jitter=lambda maximum: 0.0,
                    )
                    with self.assertRaises(ProviderExecutionError):
                        await service.analyze_product_image(synthetic_png(), "en")
                self.assertEqual(len(requests), 1)

    async def test_malformed_json_and_schema_failures_are_not_retried(self):
        malformed = httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "not-json"}}
                ]
            },
        )
        requests = []
        transport = sequence_transport([malformed], requests)

        with patch.dict(os.environ, external_settings(EXTERNAL_AI_MAX_RETRIES="3"), clear=False):
            service = ProductListingService(
                http_transport=transport, sleeper=AsyncMock(), jitter=lambda maximum: 0.0
            )
            with self.assertRaises(ProviderExecutionError) as raised:
                await service.analyze_product_image(synthetic_png(), "en")

        self.assertEqual(len(requests), 1)
        self.assertEqual(raised.exception.telemetry.failure_category, "output_validation")

        invalid_schema = httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "title": "Desk organizer",
                                    "description": "Synthetic draft",
                                    "tags": ["desk", "storage", "workspace", "minimalist"],
                                }
                            )
                        }
                    }
                ]
            },
        )
        schema_requests = []
        with patch.dict(os.environ, external_settings(EXTERNAL_AI_MAX_RETRIES="3"), clear=False):
            service = ProductListingService(
                http_transport=sequence_transport([invalid_schema], schema_requests),
                sleeper=AsyncMock(),
                jitter=lambda maximum: 0.0,
            )
            with self.assertRaises(ProviderExecutionError):
                await service.analyze_product_image(synthetic_png(), "en")
        self.assertEqual(len(schema_requests), 1)

    async def test_circuit_open_prevents_external_request(self):
        requests = []
        transport = sequence_transport([httpx.Response(503)], requests)

        with patch.dict(
            os.environ,
            external_settings(
                EXTERNAL_AI_MAX_RETRIES="0", EXTERNAL_AI_CIRCUIT_FAILURE_THRESHOLD="1"
            ),
            clear=False,
        ):
            service = ProductListingService(
                http_transport=transport, sleeper=AsyncMock(), jitter=lambda maximum: 0.0
            )
            with self.assertRaises(ProviderExecutionError):
                await service.analyze_product_image(synthetic_png(), "en")
            with self.assertRaises(ProviderExecutionError) as raised:
                await service.analyze_product_image(synthetic_png(), "en")

        self.assertEqual(len(requests), 1)
        self.assertEqual(raised.exception.telemetry.attempts, 0)
        self.assertEqual(raised.exception.telemetry.failure_category, "circuit_open")
        self.assertEqual(raised.exception.telemetry.circuit_state.value, "OPEN")

    async def test_half_open_probe_recovers_and_closes_circuit(self):
        requests = []
        transport = sequence_transport([httpx.Response(503), valid_provider_response()], requests)
        current_time = [0.0]
        breaker = ProcessLocalCircuitBreaker(
            failure_threshold=1, cooldown_seconds=10.0, clock=lambda: current_time[0]
        )

        with patch.dict(
            os.environ, external_settings(EXTERNAL_AI_MAX_RETRIES="0"), clear=False
        ):
            service = ProductListingService(
                http_transport=transport,
                circuit_breaker=breaker,
                sleeper=AsyncMock(),
                jitter=lambda maximum: 0.0,
            )
            with self.assertRaises(ProviderExecutionError):
                await service.analyze_product_image(synthetic_png(), "en")
            with self.assertRaises(ProviderExecutionError):
                await service.analyze_product_image(synthetic_png(), "en")
            current_time[0] = 10.0
            listing = await service.analyze_product_image(synthetic_png(), "en")

        self.assertEqual(len(requests), 2)
        self.assertEqual(breaker.state.value, "CLOSED")
        self.assertIn("attempts=1", listing.provider_trace)
        self.assertIn("circuit=CLOSED", listing.provider_trace)

    async def test_mock_mode_makes_zero_external_calls_with_transport(self):
        requests = []
        transport = sequence_transport([valid_provider_response()], requests)
        settings = external_settings(MOCK_AI_MODE="true")

        with patch.dict(os.environ, settings, clear=False):
            listing = await ProductListingService(
                http_transport=transport
            ).analyze_product_image(synthetic_png(), "en")

        self.assertEqual(len(requests), 0)
        self.assertEqual(listing.provider, "mock")
        self.assertEqual(listing.provider_trace, "deterministic-local-v1; external_calls=0")

    def test_invalid_retry_configuration_fails_before_provider_call(self):
        for name, value in (
            ("EXTERNAL_AI_CONNECT_TIMEOUT_SECONDS", "0"),
            ("EXTERNAL_AI_READ_TIMEOUT_SECONDS", "0"),
            ("EXTERNAL_AI_REQUEST_TIMEOUT_SECONDS", "0"),
            ("EXTERNAL_AI_MAX_RETRIES", "-1"),
            ("EXTERNAL_AI_RETRY_MAX_BACKOFF_SECONDS", "31"),
            ("EXTERNAL_AI_CIRCUIT_FAILURE_THRESHOLD", "0"),
        ):
            with self.subTest(name=name):
                with patch.dict(
                    os.environ, external_settings(**{name: value}), clear=False
                ):
                    with self.assertRaises(ProviderConfigurationError):
                        ProductListingService()

    def test_retry_delay_is_bounded_and_jitter_is_injectable(self):
        from provider_resilience import ResilienceConfig, retry_delay

        config = ResilienceConfig(
            retry_backoff_seconds=2.0,
            retry_max_backoff_seconds=3.0,
            retry_jitter_seconds=1.0,
        )
        self.assertEqual(retry_delay(0, config, jitter=lambda maximum: 0.5), 2.5)
        self.assertEqual(retry_delay(3, config, jitter=lambda maximum: 1.0), 3.0)


if __name__ == "__main__":
    unittest.main()
