# Portfolio Review

## Reviewer checklist

- Run the mock-only backend and Next.js UI without an API key.
- Upload `fixtures/images/synthetic_desk_organizer.ppm`.
- Confirm the title, description, tags, warnings, and trace are deterministic.
- Run the backend tests and repository guardrail.
- Generate and inspect `reports/local_product_listing_report.md`.
- Inspect `.github/workflows/ci.yml` for the secret-free CI path.

## Evidence commands

```powershell
python -m unittest discover -s tests -v
python scripts/check_repo_guardrails.py
python scripts/generate_local_product_listing_report.py
Get-Content reports/local_product_listing_report.md
```

## Engineering evidence

| Skill | Repository evidence |
| --- | --- |
| Generative workflow | Explicit mock/external routing and structured output validation |
| Multimodal API | In-memory image upload boundary and optional external image path |
| Safety | Explicit external opt-in, generic errors, no filename logging |
| Evaluation | Synthetic fixture, deterministic output, warnings, routing trace |
| Full stack | FastAPI backend and Next.js upload interface |
| Delivery | Backend tests, frontend lint/build, guardrail, GitHub Actions CI |

## Known limitations

Mock mode does not inspect pixels. External drafts may hallucinate. Language variants are not professionally translated. No marketplace approval, legal compliance, ranking, or sales outcome is guaranteed. Uploaded content should be treated as sensitive whenever optional external mode is used.
