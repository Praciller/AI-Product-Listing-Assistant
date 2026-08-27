# Portfolio Review

## Reviewer checklist

- Run the mock-only backend and Next.js UI without an API key.
- Upload `fixtures/images/synthetic_desk_organizer.png`.
- Confirm the title, description, tags, warnings, and trace are deterministic.
- Confirm the generated report records 4/4 title, category, style, and intended-use contract
  checks while clearly excluding visual-accuracy claims.
- Run the backend tests and repository guardrail.
- Generate and inspect `reports/local_product_listing_report.md`.
- Inspect the [verified mock result screenshot](screenshots/product-listing-mock.png).
- Inspect `.github/workflows/ci.yml` for the secret-free CI path.

## Evidence commands

```powershell
python -m unittest discover -s tests -v
python scripts/check_repo_guardrails.py
python scripts/generate_local_product_listing_report.py
Get-Content reports/local_product_listing_report.md
npm run lint --prefix frontend
npm run build --prefix frontend
git diff --check
```

## Engineering evidence

| Skill | Repository evidence |
| --- | --- |
| GenAI integration | Explicit mock/external routing and structured output validation |
| Multimodal API | Bounded JPEG/PNG/WebP upload validation and optional external image path |
| Safety | Signature/decode/pixel checks, restricted CORS, external-provider opt-in, generic errors |
| Evaluation | Synthetic fixture, 4-field contract evaluation, warnings, provider trace |
| Full stack | FastAPI backend and Next.js upload interface |
| Delivery | Backend tests, frontend lint/build, guardrail, GitHub Actions CI |

## Known limitations

The 4/4 result evaluates deterministic title/category/attribute expectations, not image
understanding. Mock mode validates the upload but does not use its pixels to create the draft.
External-model drafts may hallucinate. Language variants are not professionally translated. No
marketplace approval, legal compliance, ranking, or sales outcome is guaranteed. Uploaded content
should be treated as sensitive whenever optional external mode is used. Application-level size
validation does not replace a hosting-platform request-body limit, authentication, malware
scanning, or rate limiting. The optional route has a process-local circuit breaker; its state is
not shared across serverless instances.
