# AI Product Listing Assistant

Portfolio demonstration of a mock-first multimodal listing workflow. A FastAPI backend and Next.js interface turn an uploaded image into a structured draft title, description, and tags. The default path is deterministic, offline, and requires no API key, paid service, or real product photo.

## What this demonstrates

- Explicit provider routing with offline mock mode as the safe default.
- Optional Gemini image analysis behind three opt-in settings.
- Structured multilingual draft output with warnings and provider trace.
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

Open `http://localhost:3000`. No `.env` file is required. Use `fixtures/images/synthetic_desk_organizer.ppm` for a synthetic upload.

## Deterministic evidence

```powershell
python scripts/generate_local_product_listing_report.py
Get-Content reports/local_product_listing_report.md
```

The ignored report records the synthetic fixture metadata, deterministic draft, warnings, validation status, and `external_calls=0` provider trace. See [local review](docs/local_review.md) for the API smoke test.

## Optional Gemini mode

Gemini is never selected only because an API key exists. Set every opt-in value explicitly:

```powershell
$env:AI_PROVIDER="gemini"
$env:MOCK_AI_MODE="false"
$env:ENABLE_EXTERNAL_AI="true"
$env:GOOGLE_API_KEY="your_google_ai_studio_key_here"
python -m uvicorn main:app --app-dir api --reload
```

If the key or external-AI opt-in is missing, startup fails with a configuration error. Provider failures return a generic error and do not expose secret values.

## Architecture

```text
Synthetic or user-selected image
  -> Next.js upload UI
  -> FastAPI /generate-product-info
  -> explicit provider router
     -> mock: deterministic local draft, no network
     -> gemini: optional image analysis
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

- Uploaded images are processed in memory and are not written by the API.
- Upload, generated-report, cache, database, environment, and build paths are ignored.
- Repository guardrails reject secret-shaped values, private upload paths, unapproved images, local databases, files over 5 MiB, and unsafe unqualified claims.
- Only synthetic fixtures and documented UI screenshots belong in the repository.

## Limitations

- Mock mode proves routing, schema, UI integration, and deterministic evidence; it does not infer pixels.
- Gemini output can hallucinate attributes and must be reviewed before publication.
- Multilingual wording is generated, not professionally translated or culturally validated.
- No marketplace acceptance, legal compliance, conversion lift, or search ranking is promised.
- The project has no retry or circuit-breaker implementation; provider failures are surfaced cleanly.

## Documentation

- [Local review guide](docs/local_review.md)
- [Portfolio reviewer checklist](docs/portfolio_review.md)
- [Product listing methodology](docs/product_listing_methodology.md)

## License

MIT
