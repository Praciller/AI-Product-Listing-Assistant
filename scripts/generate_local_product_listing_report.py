import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from product_listing_service import ProductListingService  # noqa: E402
from product_listing_evaluation import evaluate_listing  # noqa: E402


async def main() -> None:
    os.environ.update(
        AI_PROVIDER="mock", MOCK_AI_MODE="true", ENABLE_EXTERNAL_AI="false"
    )
    fixture_path = ROOT / "fixtures" / "products" / "synthetic_desk_organizer.json"
    image_path = ROOT / "fixtures" / "images" / "synthetic_desk_organizer.png"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    listing = await ProductListingService().analyze_product_image(
        image_path.read_bytes(), fixture["language"]
    )
    evaluation = evaluate_listing(listing, fixture["evaluation"])

    lines = [
        "# Local Product Listing Report",
        "",
        f"- Fixture: `{fixture['fixture_id']}` (synthetic)",
        "- Deterministic: yes",
        "- External AI calls: none",
        f"- Provider trace: `{listing['provider_trace']}`",
        f"- Validation status: `{listing['validation_status']}`",
        "",
        "## Resilience boundary",
        "",
        "- Route under test: `mock`",
        "- External inference calls: `0`",
        "- Resilience mode: external HTTP boundary is bypassed by design",
        "- External timeout/retry/circuit evidence: covered separately by the unittest suite with mocked HTTP transport",
        "",
        "## Synthetic input context",
        "",
        *[f"- {key}: {value}" for key, value in fixture["known_context"].items()],
        f"- Unknowns: {', '.join(fixture['unknowns'])}",
        "",
        "## Field-level contract evaluation",
        "",
        evaluation["scope"],
        "",
        "| Field | Expected | Observed evidence | Result |",
        "| --- | --- | --- | --- |",
        *[
            (
                f"| {item['field']} | {item['expected']} | {item['evidence']} | "
                f"{'PASS' if item['passed'] else 'FAIL'} |"
            )
            for item in evaluation["field_results"]
        ],
        "",
        (
            f"Result: {evaluation['passed_fields']}/{evaluation['total_fields']} fields passed. "
            "This evaluates the deterministic mock contract, not visual-model accuracy."
        ),
        "",
        "## Generated draft",
        "",
        f"**Title:** {listing['title']}",
        "",
        listing["description"],
        "",
        f"**Tags:** {', '.join(listing['tags'])}",
        "",
        "## Warnings and limitations",
        "",
        *[f"- {warning}" for warning in listing["warnings"]],
        "- Demo content is not guaranteed to satisfy legal or marketplace requirements.",
        "",
    ]
    output = ROOT / "reports" / "local_product_listing_report.md"
    output.parent.mkdir(exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    asyncio.run(main())
