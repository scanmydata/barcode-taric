import unittest
import urllib.error
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from taric_lookup import (
    best_taric_match,
    fetch_openfoodfacts_product,
    load_inputs,
    normalize_to_ean13,
    parser_rewrite_to_customs_text,
    resolve_item,
)


class TaricLookupTests(unittest.TestCase):
    def test_normalize_ean13_from_12_digits(self):
        self.assertEqual(normalize_to_ean13("123456789012"), "1234567890128")

    def test_normalize_ean13_from_8_digits(self):
        self.assertEqual(normalize_to_ean13("12345678"), "0000012345678")

    def test_normalize_ean13_invalid_length(self):
        self.assertIsNone(normalize_to_ean13("12345"))

    def test_parser_rewrites_greek_terms(self):
        text = parser_rewrite_to_customs_text("Ανδρικό βαμβακερό πουκάμισο μακρυμάνικο")
        self.assertIn("mens", text)
        self.assertIn("cotton", text)
        self.assertIn("shirt", text)

    def test_best_taric_match_for_laptop(self):
        match = best_taric_match("portable laptop computer")
        self.assertIsNotNone(match)
        self.assertEqual(match.hs4, "8471")

    def test_best_taric_match_returns_none_when_no_match(self):
        self.assertIsNone(best_taric_match("zzqv totally unrelated product text"))

    def test_load_inputs_from_xlsx_with_mocked_openpyxl(self):
        class FakeSheet:
            def iter_rows(self, values_only=True):
                return iter([(None, " 5201005080027 "), ("Laptop", "")])

        class FakeWorkbook:
            worksheets = [FakeSheet()]

        fake_module = ModuleType("openpyxl")
        fake_module.load_workbook = lambda filename, read_only, data_only: FakeWorkbook()  # type: ignore[attr-defined]
        with patch.dict("sys.modules", {"openpyxl": fake_module}):
            values = load_inputs(Path("/tmp/any.xlsx"))
        self.assertEqual(values, ["5201005080027", "Laptop"])

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

    @patch("taric_lookup._http_json", side_effect=urllib.error.URLError("network down"))
    def test_openfoodfacts_network_failure(self, _mock_http):
        result = fetch_openfoodfacts_product("5201005080027")
        self.assertEqual(result["source"], "OpenFoodFacts")
        self.assertFalse(result["found"])
        self.assertEqual(result["error"], "request_failed")


if __name__ == "__main__":
    unittest.main()
