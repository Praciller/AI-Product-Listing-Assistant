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
Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue

python -m uvicorn main:app --app-dir api
```

Keep that process open. In another PowerShell window:

```powershell
cd C:\path\to\AI-Product-Listing-Assistant
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev --prefix frontend
```

Open `http://localhost:3000`, upload `fixtures/images/synthetic_desk_organizer.ppm`, select English, and analyze it.

Expected result:

- Title: `Minimalist Reusable Desk Organizer`
- Provider: `mock`
- Validation status: `draft`
- Trace: `deterministic-local-v1; external_calls=0`
- Warnings state that attributes need verification and the draft has no marketplace guarantee.

## Backend-only smoke test

With the backend running:

```powershell
curl.exe -s -X POST http://localhost:8000/generate-product-info `
  -F "file=@fixtures/images/synthetic_desk_organizer.ppm;type=image/x-portable-pixmap" `
  -F "language=en"
```

The response should have `success: true` and `data.provider: mock`.

## Evidence and checks

```powershell
python -m unittest discover -s tests -v
python scripts/check_repo_guardrails.py
python scripts/generate_local_product_listing_report.py
Get-Content reports/local_product_listing_report.md
```

The generated report is intentionally ignored by Git.
