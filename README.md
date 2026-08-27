# AI Product Listing Assistant

Portfolio demonstration of a mock-first multimodal listing workflow. A FastAPI backend and Next.js interface turn an uploaded image into a structured draft title, description, and tags. The default path is deterministic, offline, and requires no API key, paid service, or real product photo.

## What this demonstrates

- Explicit provider routing with offline mock mode as the safe default.
- Optional vendor-neutral external image analysis behind explicit opt-in settings.
- Signature-verified JPEG, PNG, and WebP uploads with bounded size and pixels.
- Typed multilingual draft output with warnings and provider trace.
- Synthetic test evidence, privacy guardrails, backend tests, and CI.
- FastAPI service boundaries and a Next.js upload interface.

Generated copy is decision-support draft content. It is not legal advice, a marketplace approval, or a guarantee of search performance.

## Zero-cost local quickstart

Python 3.11+ and Node.js 20+ are expected. In PowerShell:

```powershell
git clone https://github.com/Praciller/AI-Product-Listing-Assistant.git
cd AI-Product-Listing-Assistant

python -m pip install -r api/requirements.txt
npm ci --prefix frontend

$env:AI_PROVIDER="mock"
$env:MOCK_AI_MODE="true"
$env:ENABLE_EXTERNAL_AI="false"

python -m uvicorn main:app --app-dir api --reload
```

In a second PowerShell window:

```powershell
cd AI-Product-Listing-Assistant
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev --prefix frontend
```

Open `http://localhost:3000`. No `.env` file is required. Use `fixtures/images/synthetic_desk_organizer.png` for a synthetic upload.

## Deterministic evidence

```powershell
python scripts/generate_local_product_listing_report.py
Get-Content reports/local_product_listing_report.md
```

The ignored report records the synthetic fixture metadata, deterministic draft, warnings,
validation status, `external_calls=0` provider trace, and a 4-field title/category/attribute
contract evaluation. This is mock-contract evidence, not visual-model accuracy. See
[local review](docs/local_review.md) for the API smoke test and
[the reviewer screenshot](docs/screenshots/product-listing-mock.png) for the verified UI state.

## Optional external mode

External inference is never selected only because an API key exists. Set every opt-in value explicitly:

```powershell
$env:AI_PROVIDER="external"
$env:MOCK_AI_MODE="false"
$env:ENABLE_EXTERNAL_AI="true"
$env:EXTERNAL_AI_ENDPOINT="https://your-inference-endpoint.example/v1/messages"
$env:EXTERNAL_AI_API_KEY="your_provider_key_here"
$env:EXTERNAL_AI_MODEL="your-model"
$env:EXTERNAL_AI_CONNECT_TIMEOUT_SECONDS="5"
$env:EXTERNAL_AI_READ_TIMEOUT_SECONDS="30"
$env:EXTERNAL_AI_REQUEST_TIMEOUT_SECONDS="45"
$env:EXTERNAL_AI_MAX_RETRIES="1"
$env:EXTERNAL_AI_RETRY_BACKOFF_SECONDS="0.25"
$env:EXTERNAL_AI_RETRY_MAX_BACKOFF_SECONDS="5"
$env:EXTERNAL_AI_RETRY_JITTER_SECONDS="0.1"
$env:EXTERNAL_AI_CIRCUIT_FAILURE_THRESHOLD="3"
$env:EXTERNAL_AI_CIRCUIT_COOLDOWN_SECONDS="30"
python -m uvicorn main:app --app-dir api --reload
```

If any endpoint, key, model, or external-AI opt-in value is missing, startup fails with a configuration error. The route expects an OpenAI-compatible JSON response shape (`choices[0].message.content`) but remains vendor-neutral and uses no provider SDK. It has explicit connect/read timeouts and a bounded overall deadline. One retry is allowed by default only for network/timeout errors, HTTP 429, and selected transient 5xx responses. Authentication, configuration, invalid input, malformed JSON, and schema failures are not retried. Provider failures return a generic error and do not expose secret values. See [provider resilience](docs/provider_resilience.md) for the exact policy and evidence.

## Configuration

- `CORS_ORIGINS`: comma-separated HTTP(S) origins. Defaults to `http://localhost:3000,http://127.0.0.1:3000`; wildcard origins are rejected. Credentials are disabled and browser CORS is limited to `POST` with `Content-Type`.
- `MAX_UPLOAD_SIZE_BYTES`: upload ceiling, default `5242880` (5 MiB), bounded to 1-25 MiB.
- `MAX_IMAGE_PIXELS`: decoded-image pixel ceiling, default `25000000`, maximum `50000000`.
- `EXTERNAL_AI_ENDPOINT`: configured vendor-neutral inference URL. It is required only for external mode and is never included in telemetry.
- `EXTERNAL_AI_API_KEY`: external provider credential. It is required only for external mode and is never logged or returned.
- `EXTERNAL_AI_MODEL`: model identifier sent to the configured endpoint.
- `EXTERNAL_AI_CONNECT_TIMEOUT_SECONDS`: connection/pool timeout, default 5 seconds, range 0.01-30.
- `EXTERNAL_AI_READ_TIMEOUT_SECONDS`: per-attempt response timeout, default 30 seconds, range 0.01-120. `EXTERNAL_AI_TIMEOUT_SECONDS` is accepted as a legacy alias when this setting is absent.
- `EXTERNAL_AI_REQUEST_TIMEOUT_SECONDS`: overall operation deadline across attempts and backoff, default 45 seconds, range 0.01-300.
- `EXTERNAL_AI_MAX_RETRIES`: transient retries after the first attempt, default 1, range 0-3.
- `EXTERNAL_AI_RETRY_BACKOFF_SECONDS`: initial exponential backoff, default 0.25 seconds, range 0-5.
- `EXTERNAL_AI_RETRY_MAX_BACKOFF_SECONDS`: maximum backoff including jitter, default 5 seconds, range 0-30.
- `EXTERNAL_AI_RETRY_JITTER_SECONDS`: injected random jitter ceiling, default 0.1 seconds, range 0-5.
- `EXTERNAL_AI_CIRCUIT_FAILURE_THRESHOLD`: consecutive exhausted transient operations before opening, default 3, range 1-10.
- `EXTERNAL_AI_CIRCUIT_COOLDOWN_SECONDS`: open-state cooldown before one half-open probe, default 30 seconds, range 0.01-300.

## Architecture

```text
Synthetic or user-selected image
  -> Next.js upload UI
  -> FastAPI /generate-product-info
  -> explicit provider router
     -> mock: deterministic local draft, no network
     -> external: optional bounded HTTP analysis
  -> validated title, description, tags, warnings, trace
```

## Verification

```powershell
python -m unittest discover -s tests -v
python scripts/check_repo_guardrails.py
python scripts/generate_local_product_listing_report.py
npm run lint --prefix frontend
npm run build --prefix frontend
git diff --check
```

CI runs the same mock-only path without secrets.

## Privacy and safety

- The endpoint reads uploads in 64 KiB chunks and retains at most the configured limit plus one byte. FastAPI's multipart layer may spool an upload to temporary storage before endpoint validation; the application closes the upload and does not persist it.
- Declared MIME type, JPEG/PNG/WebP signature, Pillow format, full decode, and pixel count must agree before provider routing.
- External mode sends the validated image to the configured endpoint only after all explicit opt-in and endpoint/key/model settings are present. Mock mode makes no external AI call.
- CORS is a browser-origin control, not authentication or authorization.
- Upload, generated-report, cache, database, environment, and build paths are ignored.
- Repository guardrails reject secret-shaped values, private upload paths, unapproved images, local databases, files over 5 MiB, and unsafe unqualified claims.
- Only synthetic fixtures and documented UI screenshots belong in the repository.

## Limitations

- Mock mode proves routing, schema, UI integration, and deterministic evidence; it does not infer pixels.
- External-model output can hallucinate attributes and must be reviewed before publication.
- Multilingual wording is generated, not professionally translated or culturally validated.
- No marketplace acceptance, legal compliance, conversion lift, or search ranking is promised.
- Application-level upload checks do not replace a reverse-proxy or hosting-platform request-body limit.
- The external route has bounded connect/read/overall timeouts, a small retry budget, and a process-local circuit breaker; this is not distributed fault tolerance.
- Circuit state is process-local and is not shared across serverless instances. Restarts and new serverless instances reset the circuit.
- Retries can increase latency and consume additional provider quota; retry exhaustion still returns a generic failure.
- There is no queue, rate limiter, authentication layer, malware scanner, or persistent audit store.

## Documentation

- [Local review guide](docs/local_review.md)
- [Portfolio reviewer checklist](docs/portfolio_review.md)
- [Product listing methodology](docs/product_listing_methodology.md)
- [Provider routing and resilience](docs/provider_resilience.md)

## License

MIT
