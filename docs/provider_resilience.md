# Provider Routing and Resilience

The application has two explicit routes:

- `mock`: deterministic and local. It is the default and makes zero external
  inference calls, even when external settings are present.
- `external`: optional vendor-neutral external HTTP inference. It is selected
  only when `MOCK_AI_MODE=false`, `AI_PROVIDER=external`,
  `ENABLE_EXTERNAL_AI=true`, and endpoint, API-key, and model settings are all
  present.

## Bounded request policy

The external route uses a small HTTP boundary with no provider SDK retry layer.
Each HTTP attempt has explicit connection/pool, read, write, and an outer
overall operation timeout. The overall deadline includes retries and backoff;
there is no wait-forever path.

The safe defaults are:

| Setting | Default | Bound |
| --- | ---: | ---: |
| Connect/pool timeout | 5 seconds | 0.01-30 |
| Read/write timeout | 30 seconds | 0.01-120 |
| Overall request timeout | 45 seconds | 0.01-300 |
| Maximum retries | 1 | 0-3 |
| Initial backoff | 0.25 seconds | 0-5 |
| Maximum backoff | 5 seconds | 0-30 |
| Jitter ceiling | 0.1 seconds | 0-5 |

`EXTERNAL_AI_TIMEOUT_SECONDS` is retained as a legacy alias for the read
timeout when `EXTERNAL_AI_READ_TIMEOUT_SECONDS` is not set. Gemini-prefixed
settings remain compatibility aliases; new deployments should use
`EXTERNAL_AI_*` names.

## Retry matrix

Retries are counted after the first request, and the maximum outbound attempts
are always `EXTERNAL_AI_MAX_RETRIES + 1`.

| Failure | Retry? | Category |
| --- | --- | --- |
| Connect/read/write/pool network error | Yes, within budget | `network` or `timeout` |
| HTTP 408 or 425 | Yes, within budget | `http_timeout` |
| HTTP 429 | Yes, within budget | `http_429` |
| HTTP 500, 502, 503, 504 | Yes, within budget | `http_5xx` |
| HTTP 400 | No | `http_4xx` |
| HTTP 401 or 403 | No | `http_4xx` |
| Other 4xx/5xx statuses | No by default | `http_4xx` or `provider_error` |
| Malformed provider JSON/output shape/schema | No | `output_validation` |

Backoff is bounded exponential delay with an injectable jitter function. Tests
inject a zero-jitter function and a no-op async sleeper, so they do not sleep
for seconds or contact a provider.

## Circuit breaker

A small process-local circuit breaker protects the external route after
consecutive exhausted transient operations:

- `CLOSED`: requests are allowed; successful calls reset the transient failure
  count.
- `OPEN`: external requests are rejected immediately until the cooldown
  expires.
- `HALF_OPEN`: one probe is allowed after cooldown. Success returns to `CLOSED`;
  another transient failure returns to `OPEN`.

Permanent HTTP failures and output validation failures do not consume the
transient health budget. The breaker is deliberately local to the service
process. Circuit state is process-local and is not shared across serverless
instances. Restarts and new instances reset it; this is not distributed fault
tolerance.

## Safe telemetry and failure handling

Successful external responses include a bounded provider trace containing only
the route, attempts, retry count, failure category, fallback state, degraded
state, circuit state, and response-schema status. Failure logs use the same
classification fields. Client errors remain generic.

The implementation never places the API key, authorization header, provider
headers, endpoint URL, or raw provider error body in client-visible diagnostics
or resilience telemetry. Retries can increase latency and provider quota use;
exhaustion remains a visible generic failure rather than a silent mock fallback.

## Deterministic evidence

The backend suite uses `httpx.MockTransport` to cover first-attempt success,
timeout recovery, 429 recovery, selected 5xx recovery, exact retry exhaustion,
permanent 400/401/403 failures, malformed output, open-circuit short-circuiting,
half-open recovery, bounded overall timeout, configuration validation, and
mock-mode zero external calls. Run:

```powershell
python -m unittest discover -s tests -v
python scripts/check_repo_guardrails.py
python scripts/generate_local_product_listing_report.py
```

The generated local report intentionally exercises only the mock route. Its
`external_calls=0` result is deterministic routing evidence, not live-provider
or visual-model accuracy evidence.
