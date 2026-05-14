import unittest
from unittest.mock import patch

from taric_lookup import (
    best_taric_match,
    normalize_to_ean13,
    parser_rewrite_to_customs_text,
    resolve_item,
)


class TaricLookupTests(unittest.TestCase):
    def test_normalize_ean13_from_12_digits(self):
        self.assertEqual(normalize_to_ean13("123456789012"), "1234567890128")

    def test_parser_rewrites_greek_terms(self):
        text = parser_rewrite_to_customs_text("Ανδρικό βαμβακερό πουκάμισο μακρυμάνικο")
        self.assertIn("mens", text)
        self.assertIn("cotton", text)
        self.assertIn("shirt", text)

    def test_best_taric_match_for_laptop(self):
        match = best_taric_match("portable laptop computer")
        self.assertIsNotNone(match)
        self.assertEqual(match.hs4, "8471")

    @patch("taric_lookup.ai_rewrite_to_customs_text", return_value=None)
    @patch("taric_lookup.fetch_openfoodfacts_product")
    def test_resolve_item_uses_openfoodfacts_for_barcode(self, mock_off, _mock_ai):
        mock_off.return_value = {
            "source": "OpenFoodFacts",
            "found": True,
            "product_name": "Natural Mineral Water",
            "categories": "Waters",
            "brand": "Demo",
        }
        result = resolve_item("5201005080027", ai_provider="none")
        self.assertEqual(result["barcode"], "5201005080027")
        self.assertEqual(result["match"]["hs4"], "2201")


if __name__ == "__main__":
    unittest.main()
