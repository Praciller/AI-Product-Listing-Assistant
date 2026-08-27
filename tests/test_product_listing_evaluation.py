import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from product_listing_evaluation import evaluate_listing
from product_listing_service import ProductListing


EVALUATION = {
    "scope": "Contract-level synthetic fixture; mock mode does not infer image pixels.",
    "fields": [
        {
            "field": "title",
            "match": "exact",
            "expected": "Minimalist Reusable Desk Organizer",
            "sources": ["title"],
        },
        {
            "field": "category",
            "match": "contains",
            "expected": "desk organizer",
            "sources": ["title", "tags"],
        },
        {
            "field": "style",
            "match": "contains",
            "expected": "minimalist",
            "sources": ["title", "tags"],
        },
        {
            "field": "intended_use",
            "match": "contains",
            "expected": "storage",
            "sources": ["description", "tags"],
        },
    ],
}


def listing(title: str = "Minimalist Reusable Desk Organizer") -> ProductListing:
    return ProductListing(
        title=title,
        description="A compact organizer for small desk-item storage.",
        tags=["desk organizer", "minimalist", "reusable", "workspace", "storage"],
        language="English",
        warnings=["Synthetic mock output; review before publishing."],
        validation_status="draft",
        provider="mock",
        provider_trace="deterministic-local-v1; external_calls=0",
    )


class ProductListingEvaluationTests(unittest.TestCase):
    def test_field_level_fixture_evaluation_passes_expected_mock_contract(self):
        result = evaluate_listing(listing(), EVALUATION)

        self.assertTrue(result["all_passed"])
        self.assertEqual(result["passed_fields"], 4)
        self.assertEqual(result["total_fields"], 4)
        self.assertEqual(
            [item["field"] for item in result["field_results"]],
            ["title", "category", "style", "intended_use"],
        )

    def test_exact_title_mismatch_is_reported_without_hiding_other_fields(self):
        result = evaluate_listing(listing("Reusable Desk Organizer"), EVALUATION)

        self.assertFalse(result["all_passed"])
        self.assertEqual(result["passed_fields"], 3)
        self.assertFalse(result["field_results"][0]["passed"])
        self.assertEqual(
            result["field_results"][0]["evidence"], "Reusable Desk Organizer"
        )


if __name__ == "__main__":
    unittest.main()
