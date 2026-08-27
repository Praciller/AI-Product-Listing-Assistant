# Local Review

This path is local, deterministic, and does not contact an AI provider.

## Setup and run

```powershell
cd C:\path\to\AI-Product-Listing-Assistant
python -m pip install -r api/requirements.txt
npm ci --prefix frontend

$env:AI_PROVIDER="mock"
$env:MOCK_AI_MODE="true"
$env:ENABLE_EXTERNAL_AI="false"
$env:CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
Remove-Item Env:EXTERNAL_AI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:EXTERNAL_AI_ENDPOINT -ErrorAction SilentlyContinue

python -m uvicorn main:app --app-dir api
```

Keep that process open. In another PowerShell window:

```powershell
cd C:\path\to\AI-Product-Listing-Assistant
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev --prefix frontend
```

Open `http://localhost:3000`, upload `fixtures/images/synthetic_desk_organizer.png`, select English, and analyze it.

Expected result:

- Title: `Minimalist Reusable Desk Organizer`
- Provider: `mock`
- Validation status: `draft`
- Trace: `deterministic-local-v1; external_calls=0`
- Warnings state that attributes need verification and the draft has no marketplace guarantee.

The verified desktop result is captured in
[product-listing-mock.png](screenshots/product-listing-mock.png). It shows the synthetic image,
typed draft fields, provider/status labels, and the human-review warning.

## Backend-only smoke test

With the backend running:

```powershell
curl.exe -s -X POST http://localhost:8000/generate-product-info `
  -F "file=@fixtures/images/synthetic_desk_organizer.png;type=image/png" `
  -F "language=en"
```

The response should have `success: true`, `data.provider: mock`, five tags, warnings, and `external_calls=0` in the provider trace. The endpoint accepts only JPEG, PNG, and WebP after MIME, signature, decode, and pixel-limit validation.

## Evidence and checks

```powershell
python -m unittest discover -s tests -v
python scripts/check_repo_guardrails.py
python scripts/generate_local_product_listing_report.py
Get-Content reports/local_product_listing_report.md
npm run lint --prefix frontend
npm run build --prefix frontend
git diff --check
```

The backend suite covers upload size/type/signature/decode/pixel failures, CORS parsing, typed
output bounds, mock isolation, bounded connection/read/overall timeouts, exact transient retry
classification, non-retryable provider failures, process-local circuit transitions, and field-level
fixture evaluation. The generated report is intentionally ignored by Git. Its 4/4 result covers
deterministic title, category, style, and intended-use expectations; it does not measure
visual-model accuracy because mock mode does not infer pixels. See
[provider routing and resilience](provider_resilience.md) for the exact retry matrix and
process/serverless limitations.
