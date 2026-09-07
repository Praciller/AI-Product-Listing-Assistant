"""Grounding tests: unsupported-claim detection on external provider output.

The image cannot verify textual claims, so generated copy that matches
fixed claim-pattern categories must be surfaced as warnings for human
review instead of silently passing through.
"""

import asyncio
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from product_listing_service import ProductListingService
from test_product_listing_service import (
    external_settings,
    sequence_transport,
)


def synthetic_png():
    output = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(output, format="PNG")
    return output.getvalue()


def provider_response(title, description, tags):
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "title": title,
                                "description": description,
                                "tags": tags,
                            }
                        )
                    }
                }
            ]
        },
    )


def clean_response():
    return provider_response(
        "Desk organizer",
        "A compact organizer with a simple neutral finish for small desk items.",
        ["desk", "storage", "workspace", "minimalist", "reusable"],
    )


class UnsupportedClaimWarningTests(unittest.TestCase):
    def test_clean_output_gets_no_claim_warnings(self):
        with patch.dict(os.environ, external_settings(), clear=False):
            listing = asyncio.run(
                ProductListingService(
                    http_transport=sequence_transport([clean_response()], [])
                ).analyze_product_image(synthetic_png(), "en")
            )
        self.assertEqual(len(listing.warnings), 1)
        self.assertIn("AI-generated draft", listing.warnings[0])

    def test_certification_claim_is_flagged(self):
        response = provider_response(
            "Desk organizer",
            "FDA approved organizer for clinical use.",
            ["desk", "storage", "workspace", "minimalist", "reusable"],
        )
        with patch.dict(os.environ, external_settings(), clear=False):
            listing = asyncio.run(
                ProductListingService(
                    http_transport=sequence_transport([response], [])
                ).analyze_product_image(synthetic_png(), "en")
            )
        self.assertTrue(
            any("certification" in warning for warning in listing.warnings),
            listing.warnings,
        )

    def test_environmental_and_performance_claims_are_flagged(self):
        response = provider_response(
            "Eco-friendly organizer",
            "Sustainable and waterproof with a lifetime warranty.",
            ["desk", "storage", "workspace", "minimalist", "reusable"],
        )
        with patch.dict(os.environ, external_settings(), clear=False):
            listing = asyncio.run(
                ProductListingService(
                    http_transport=sequence_transport([response], [])
                ).analyze_product_image(synthetic_png(), "en")
            )
        flagged = " ".join(listing.warnings)
        self.assertIn("environmental", flagged)
        self.assertIn("performance", flagged)

    def test_word_boundaries_prevent_false_matches(self):
        response = provider_response(
            "Organizer for small parts",
            "Holds screws, unions, and fitting components without guaranteeing fit.",
            ["desk", "storage", "workspace", "minimalist", "reusable"],
        )
        with patch.dict(os.environ, external_settings(), clear=False):
            listing = asyncio.run(
                ProductListingService(
                    http_transport=sequence_transport([response], [])
                ).analyze_product_image(synthetic_png(), "en")
            )
        # "unions"/"organizer" must not trip "organic"; "guaranteeing" is
        # bounded away from "guaranteed".
        self.assertEqual(len(listing.warnings), 1)

    def test_claim_warnings_respect_five_warning_cap(self):
        response = provider_response(
            "FDA certified eco-friendly organizer",
            "Sustainable, waterproof, therapeutic, biodegradable, and guaranteed "
            "for a lifetime warranty of medical grade use.",
            ["desk", "storage", "workspace", "minimalist", "reusable"],
        )
        with patch.dict(os.environ, external_settings(), clear=False):
            listing = asyncio.run(
                ProductListingService(
                    http_transport=sequence_transport([response], [])
                ).analyze_product_image(synthetic_png(), "en")
            )
        self.assertLessEqual(len(listing.warnings), 5)
        self.assertGreater(len(listing.warnings), 1)

    def test_tags_are_also_scanned_for_claims(self):
        response = provider_response(
            "Desk organizer",
            "A compact organizer with a simple neutral finish.",
            ["desk", "storage", "workspace", "minimalist", "certified"],
        )
        with patch.dict(os.environ, external_settings(), clear=False):
            listing = asyncio.run(
                ProductListingService(
                    http_transport=sequence_transport([response], [])
                ).analyze_product_image(synthetic_png(), "en")
            )
        self.assertTrue(
            any("certification" in warning for warning in listing.warnings),
            listing.warnings,
        )


if __name__ == "__main__":
    unittest.main()
