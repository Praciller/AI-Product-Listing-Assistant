from typing import Any

from product_listing_service import ProductListing


def _source_text(listing: ProductListing, source: str) -> str:
    if source == "tags":
        return ", ".join(listing.tags)
    if source in {"title", "description"}:
        return getattr(listing, source)
    raise ValueError(f"Unsupported evaluation source: {source}")


def evaluate_listing(
    listing: ProductListing, evaluation: dict[str, Any]
) -> dict[str, Any]:
    field_results = []
    for field in evaluation["fields"]:
        expected = field["expected"]
        sources = field["sources"]
        evidence = "; ".join(_source_text(listing, source) for source in sources)
        if field["match"] == "exact":
            passed = any(
                _source_text(listing, source).casefold() == expected.casefold()
                for source in sources
            )
        elif field["match"] == "contains":
            passed = any(
                expected.casefold() in _source_text(listing, source).casefold()
                for source in sources
            )
        else:
            raise ValueError(f"Unsupported evaluation match: {field['match']}")

        field_results.append(
            {
                "field": field["field"],
                "expected": expected,
                "evidence": evidence,
                "passed": passed,
            }
        )

    passed_fields = sum(item["passed"] for item in field_results)
    return {
        "scope": evaluation["scope"],
        "field_results": field_results,
        "passed_fields": passed_fields,
        "total_fields": len(field_results),
        "all_passed": passed_fields == len(field_results),
    }
