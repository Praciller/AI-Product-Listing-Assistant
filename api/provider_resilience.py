"""Bounded, testable resilience primitives for the optional external route.

This module intentionally contains no provider SDK.  The external route uses a
small HTTP boundary so timeout, retry, and circuit behavior can be exercised
with ``httpx.MockTransport`` without credentials or network access.
"""

from __future__ import annotations

import base64
import json
import os
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

import httpx
RETRIABLE_HTTP_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class ProviderResilienceError(RuntimeError):
    """Base class for errors with a safe, classification-only surface."""


class ProviderTransportError(ProviderResilienceError):
    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


class ProviderHTTPError(ProviderResilienceError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP status {status_code}")


class ProviderOutputError(ProviderResilienceError):
    """Provider response shape/content could not be validated safely."""


def _read_float_setting(
    name: str, default: float, minimum: float, maximum: float
) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _read_int_setting(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class ResilienceConfig:
    """Validated bounds for one external inference operation."""

    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 30.0
    request_timeout_seconds: float = 45.0
    max_retries: int = 1
    retry_backoff_seconds: float = 0.25
    retry_max_backoff_seconds: float = 5.0
    retry_jitter_seconds: float = 0.1
    circuit_failure_threshold: int = 3
    circuit_cooldown_seconds: float = 30.0

    def __post_init__(self) -> None:
        bounds = (
            ("connect_timeout_seconds", self.connect_timeout_seconds, 0.01, 30.0),
            ("read_timeout_seconds", self.read_timeout_seconds, 0.01, 120.0),
            ("request_timeout_seconds", self.request_timeout_seconds, 0.01, 300.0),
            ("retry_backoff_seconds", self.retry_backoff_seconds, 0.0, 5.0),
            ("retry_max_backoff_seconds", self.retry_max_backoff_seconds, 0.0, 30.0),
            ("retry_jitter_seconds", self.retry_jitter_seconds, 0.0, 5.0),
            ("circuit_cooldown_seconds", self.circuit_cooldown_seconds, 0.01, 300.0),
        )
        for name, value, minimum, maximum in bounds:
            if not minimum <= value <= maximum:
                raise ValueError(f"{name} must be between {minimum} and {maximum}")
        if not 0 <= self.max_retries <= 3:
            raise ValueError("max_retries must be between 0 and 3")
        if not 1 <= self.circuit_failure_threshold <= 10:
            raise ValueError("circuit_failure_threshold must be between 1 and 10")

    @classmethod
    def from_environment(cls) -> "ResilienceConfig":
        def choose(primary: str, *aliases: str) -> str:
            for name in (primary, *aliases):
                if os.getenv(name) is not None:
                    return name
            return primary

        connect_name = (
            choose(
                "EXTERNAL_AI_CONNECT_TIMEOUT_SECONDS",
                "EXTERNAL_AI_CONNECTION_TIMEOUT_SECONDS",
            )
        )
        request_name = choose(
            "EXTERNAL_AI_REQUEST_TIMEOUT_SECONDS",
            "EXTERNAL_AI_OVERALL_TIMEOUT_SECONDS",
        )
        read_name = choose(
            "EXTERNAL_AI_READ_TIMEOUT_SECONDS",
            "EXTERNAL_AI_TIMEOUT_SECONDS",
        )
        return cls(
            connect_timeout_seconds=_read_float_setting(
                connect_name, 5.0, 0.01, 30.0
            ),
            read_timeout_seconds=_read_float_setting(
                read_name, 30.0, 0.01, 120.0
            ),
            request_timeout_seconds=_read_float_setting(
                request_name, 45.0, 0.01, 300.0
            ),
            max_retries=_read_int_setting(
                choose("EXTERNAL_AI_MAX_RETRIES"), 1, 0, 3
            ),
            retry_backoff_seconds=_read_float_setting(
                choose("EXTERNAL_AI_RETRY_BACKOFF_SECONDS"),
                0.25,
                0.0,
                5.0,
            ),
            retry_max_backoff_seconds=_read_float_setting(
                choose("EXTERNAL_AI_RETRY_MAX_BACKOFF_SECONDS"),
                5.0,
                0.0,
                30.0,
            ),
            retry_jitter_seconds=_read_float_setting(
                choose("EXTERNAL_AI_RETRY_JITTER_SECONDS"),
                0.1,
                0.0,
                5.0,
            ),
            circuit_failure_threshold=_read_int_setting(
                choose("EXTERNAL_AI_CIRCUIT_FAILURE_THRESHOLD"),
                3,
                1,
                10,
            ),
            circuit_cooldown_seconds=_read_float_setting(
                choose("EXTERNAL_AI_CIRCUIT_COOLDOWN_SECONDS"),
                30.0,
                0.01,
                300.0,
            ),
        )

    @property
    def max_attempts(self) -> int:
        return self.max_retries + 1


class ProcessLocalCircuitBreaker:
    """Small process-local circuit breaker for one provider route.

    Only transient, exhausted operations count against the failure budget.
    There is deliberately no shared/distributed state.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be greater than 0")
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock or time.monotonic
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._half_open_probe_in_flight = False

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def before_request(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            if (
                self._opened_at is not None
                and self._clock() - self._opened_at >= self.cooldown_seconds
            ):
                self._state = CircuitState.HALF_OPEN
                self._half_open_probe_in_flight = True
                return True
            return False
        if self._half_open_probe_in_flight:
            return False
        self._half_open_probe_in_flight = True
        return True

    def record_success(self) -> None:
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at = None
        self._half_open_probe_in_flight = False

    def record_transient_failure(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._open()
            return
        if self._state == CircuitState.OPEN:
            return
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._open()

    def record_non_transient_failure(self) -> None:
        # A permanent request/output failure is not evidence that the provider
        # is unhealthy. Close a half-open probe so it cannot remain stuck.
        if self._state == CircuitState.HALF_OPEN:
            self.record_success()
        elif self._state == CircuitState.CLOSED:
            self._consecutive_failures = 0

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        self._half_open_probe_in_flight = False


@dataclass(frozen=True)
class ProviderTelemetry:
    route: str
    attempts: int
    retry_count: int
    failure_category: str
    fallback: str
    degraded: bool
    circuit_state: CircuitState

    def trace(self, suffix: str | None = None) -> str:
        fields = (
            f"route={self.route}",
            f"attempts={self.attempts}",
            f"retries={self.retry_count}",
            f"failure={self.failure_category}",
            f"fallback={self.fallback}",
            f"degraded={'true' if self.degraded else 'false'}",
            f"circuit={self.circuit_state.value}",
        )
        if suffix:
            fields += (suffix,)
        return "; ".join(fields)


class ExternalInferenceClient:
    """Minimal vendor-neutral HTTP boundary with classification-only failures."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        config: ResilienceConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._model = model
        self._config = config
        self._transport = transport

    async def generate_content(
        self, image_data: bytes, prompt: str, mime_type: str
    ) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        self._image_part(image_data, mime_type),
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": 300,
            "response_format": {"type": "json_object"},
        }
        timeout = httpx.Timeout(
            connect=self._config.connect_timeout_seconds,
            read=self._config.read_timeout_seconds,
            write=self._config.read_timeout_seconds,
            pool=self._config.connect_timeout_seconds,
        )
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self._api_key}",
        }
        try:
            async with httpx.AsyncClient(
                timeout=timeout, transport=self._transport
            ) as client:
                response = await client.post(
                    self._endpoint, headers=headers, json=payload
                )
        except httpx.TimeoutException as exc:
            raise ProviderTransportError("timeout") from exc
        except httpx.TransportError as exc:
            raise ProviderTransportError("network") from exc

        if response.status_code >= 400:
            raise ProviderHTTPError(response.status_code)

        try:
            response_payload = response.json()
        except (TypeError, ValueError) as exc:
            raise ProviderOutputError("provider response was not valid JSON") from exc
        return self._extract_text(response_payload)

    @staticmethod
    def _image_part(image_data: bytes, mime_type: str) -> dict[str, Any]:
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,"
                + base64.b64encode(image_data).decode("ascii")
            },
        }

    @staticmethod
    def _extract_text(response_payload: Any) -> str:
        try:
            choices = response_payload["choices"]
            content = choices[0]["message"]["content"]
            if isinstance(content, list):
                text = "".join(part.get("text", "") for part in content)
            else:
                text = content
        except (KeyError, IndexError, StopIteration, TypeError) as exc:
            raise ProviderOutputError("provider response shape was invalid") from exc
        if not isinstance(text, str) or not text.strip():
            raise ProviderOutputError("provider response text was invalid")
        return text


def parse_json_text(text: str) -> Any:
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        clean = "\n".join(lines).strip()
    try:
        return json.loads(clean)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ProviderOutputError("provider output was not valid JSON") from exc


def classify_http_status(status_code: int) -> tuple[bool, str]:
    if status_code in RETRIABLE_HTTP_STATUS_CODES:
        if status_code == 429:
            return True, "http_429"
        return True, "http_5xx" if status_code >= 500 else "http_timeout"
    if 400 <= status_code < 500:
        return False, "http_4xx"
    return False, "provider_error"


def retry_delay(
    retry_index: int,
    config: ResilienceConfig,
    *,
    jitter: Callable[[float], float],
) -> float:
    exponential = min(
        config.retry_backoff_seconds * (2**retry_index),
        config.retry_max_backoff_seconds,
    )
    return min(
        config.retry_max_backoff_seconds,
        exponential + max(0.0, jitter(config.retry_jitter_seconds)),
    )


def default_jitter(maximum: float) -> float:
    return random.uniform(0.0, maximum) if maximum else 0.0
