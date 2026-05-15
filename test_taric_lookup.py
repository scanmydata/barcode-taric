import unittest
import urllib.error
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from taric_lookup import (
    best_taric_match,
    fetch_barcode_monster_product,
    fetch_barcodelookup_product,
    fetch_ean_search_product,
    fetch_go_upc_product,
    fetch_openfoodfacts_product,
    fetch_product_multi_source,
    fetch_upcitemdb_product,
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

    def test_parser_rewrites_more_greek_terms(self):
        text = parser_rewrite_to_customs_text("Υγρό ηλεκτρονικού τσιγάρου με νικοτίνη")
        self.assertIn("vape", text)
        self.assertIn("nicotine", text)

    def test_best_taric_match_for_greek_clothing_text(self):
        rewritten = parser_rewrite_to_customs_text("Ανδρικό βαμβακερό πουκάμισο")
        match = best_taric_match(rewritten)
        self.assertIsNotNone(match)
        self.assertEqual(match.hs4, "6105")

    def test_best_taric_match_prefers_nicotine_vape_entry(self):
        rewritten = parser_rewrite_to_customs_text("υγρό vape με νικοτίνη")
        match = best_taric_match(rewritten)
        self.assertIsNotNone(match)
        self.assertEqual(match.taric_code, "2404110000")

    def test_best_taric_match_for_laptop(self):
        match = best_taric_match("portable laptop computer")
        self.assertIsNotNone(match)
        self.assertEqual(match.hs4, "8471")

    def test_best_taric_match_returns_none_when_no_match(self):
        self.assertIsNone(best_taric_match("zzqv totally unrelated product text"))

    def test_best_taric_match_tie_keeps_first_highest(self):
        match = best_taric_match("water laptop")
        self.assertIsNotNone(match)
        self.assertEqual(match.hs4, "2201")

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
    @patch("taric_lookup.fetch_product_multi_source")
    def test_resolve_item_uses_openfoodfacts_for_barcode(self, mock_multi, _mock_ai):
        mock_multi.return_value = {
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
        self.assertEqual(result["error"], "network_error")

    @patch("taric_lookup._http_json")
    def test_openfoodfacts_description_field_extracted(self, mock_http):
        mock_http.return_value = {
            "status": 1,
            "product": {
                "product_name": "AVRA Water",
                "brands": "AVRA",
                "categories": "Waters",
                "generic_name": "Natural still mineral water",
            },
        }
        result = fetch_openfoodfacts_product("5201005080027")
        self.assertTrue(result["found"])
        self.assertEqual(result["description"], "Natural still mineral water")

    # ------------------------------------------------------------------
    # UPC ItemDB
    # ------------------------------------------------------------------

    @patch("taric_lookup._http_json")
    def test_fetch_upcitemdb_product_found(self, mock_http):
        mock_http.return_value = {
            "items": [{"title": "Vape liquid pear ice", "brand": "Bombo", "category": "Electronic Cigarettes", "description": "E-liquid"}]
        }
        result = fetch_upcitemdb_product("8447351005797")
        self.assertTrue(result["found"])
        self.assertEqual(result["source"], "UPCItemDB")
        self.assertEqual(result["product_name"], "Vape liquid pear ice")

    @patch("taric_lookup._http_json")
    def test_fetch_upcitemdb_product_not_found(self, mock_http):
        mock_http.return_value = {"items": []}
        result = fetch_upcitemdb_product("0000000000000")
        self.assertFalse(result["found"])
        self.assertEqual(result["source"], "UPCItemDB")

    @patch("taric_lookup._http_json", side_effect=urllib.error.URLError("down"))
    def test_fetch_upcitemdb_network_error(self, _mock_http):
        result = fetch_upcitemdb_product("8447351005797")
        self.assertFalse(result["found"])
        self.assertEqual(result["error"], "network_error")

    # ------------------------------------------------------------------
    # Barcode Monster
    # ------------------------------------------------------------------

    @patch("taric_lookup._http_json")
    def test_fetch_barcode_monster_product_found(self, mock_http):
        mock_http.return_value = {"product": "Mineral Water 500ml", "brand": "AVRA", "category": "Water"}
        result = fetch_barcode_monster_product("5201005080027")
        self.assertTrue(result["found"])
        self.assertEqual(result["source"], "BarcodeMonster")
        self.assertEqual(result["product_name"], "Mineral Water 500ml")

    @patch("taric_lookup._http_json")
    def test_fetch_barcode_monster_product_not_found(self, mock_http):
        mock_http.return_value = {}
        result = fetch_barcode_monster_product("0000000000000")
        self.assertFalse(result["found"])

    @patch("taric_lookup._http_text")
    def test_fetch_go_upc_product_parse_result(self, mock_text):
        mock_text.return_value = (
            '<h1 class="product-name">Test Product</h1>'
            '<td class="metadata-label">Brand</td><td>Demo</td>'
            '<td class="metadata-label">Category</td><td>Food</td>'
            '<h2>\n          Description\n        </h2><span>Sample item</span>'
        )
        result = fetch_go_upc_product("5201005080027")
        self.assertTrue(result["found"])
        self.assertEqual(result["source"], "GoUPC")
        self.assertEqual(result["product_name"], "Test Product")
        self.assertEqual(result["brand"], "Demo")
        self.assertEqual(result["categories"], "Food")
        self.assertEqual(result["description"], "Sample item")

    @patch("taric_lookup._http_text")
    def test_fetch_go_upc_product_not_found(self, mock_text):
        mock_text.return_value = "No product found."
        result = fetch_go_upc_product("0000000000000")
        self.assertFalse(result["found"])
        self.assertEqual(result["source"], "GoUPC")

    @patch("taric_lookup._http_text")
    def test_fetch_barcodelookup_product_parse_result(self, mock_text):
        mock_text.return_value = (
            '<title>Sample Product — Barcode Lookup</title>'
            '<td class="metadata-label">Brand</td><td>DemoBrand</td>'
            '<td class="metadata-label">Category</td><td>Electronics</td>'
            '<h2>Description</h2><div>Example description.</div>'
        )
        result = fetch_barcodelookup_product("5201005080027")
        self.assertTrue(result["found"])
        self.assertEqual(result["source"], "BarcodeLookup")
        self.assertEqual(result["product_name"], "Sample Product")
        self.assertEqual(result["brand"], "DemoBrand")
        self.assertEqual(result["categories"], "Electronics")
        self.assertEqual(result["description"], "Example description.")

    @patch("taric_lookup._http_text")
    def test_fetch_ean_search_product_parse_result(self, mock_text):
        mock_text.return_value = (
            '<title>Sample Product — EAN Search</title>'
            '<td class="metadata-label">Brand</td><td>EANBrand</td>'
            '<td class="metadata-label">Category</td><td>Household</td>'
            '<meta name="description" content="Sample item description." />'
        )
        result = fetch_ean_search_product("5201005080027")
        self.assertTrue(result["found"])
        self.assertEqual(result["source"], "EANSearch")
        self.assertEqual(result["product_name"], "Sample Product")
        self.assertEqual(result["brand"], "EANBrand")
        self.assertEqual(result["categories"], "Household")
        self.assertEqual(result["description"], "Sample item description.")

    @patch("taric_lookup._http_text")
    def test_fetch_ean_search_product_not_found(self, mock_text):
        mock_text.return_value = "No results found."
        result = fetch_ean_search_product("0000000000000")
        self.assertFalse(result["found"])
        self.assertEqual(result["source"], "EANSearch")

    # ------------------------------------------------------------------
    # Multi-source lookup
    # ------------------------------------------------------------------

    @patch("taric_lookup.fetch_barcodelookup_product")
    @patch("taric_lookup.fetch_ean_search_product")
    @patch("taric_lookup.fetch_go_upc_product")
    @patch("taric_lookup.fetch_barcode_monster_product")
    @patch("taric_lookup.fetch_upcitemdb_product")
    @patch("taric_lookup.fetch_openfoodfacts_product")
    def test_fetch_product_multi_source_returns_first_hit(self, mock_off, mock_upc, mock_monster, mock_go, mock_es, mock_bl):
        mock_off.return_value = {"source": "OpenFoodFacts", "found": True, "product_name": "AVRA Water", "brand": "AVRA", "categories": "Waters", "description": None}
        result = fetch_product_multi_source("5201005080027")
        self.assertEqual(result["source"], "OpenFoodFacts")
        mock_upc.assert_not_called()
        mock_monster.assert_not_called()

    @patch("taric_lookup.fetch_barcode_monster_product")
    @patch("taric_lookup.fetch_upcitemdb_product")
    @patch("taric_lookup.fetch_openfoodfacts_product")
    def test_fetch_product_multi_source_falls_back_to_upcitemdb(self, mock_off, mock_upc, mock_monster):
        mock_off.return_value = {"source": "OpenFoodFacts", "found": False}
        mock_upc.return_value = {"source": "UPCItemDB", "found": True, "product_name": "Vape Liquid", "brand": "Bombo", "categories": "Vape", "description": "E-liquid"}
        result = fetch_product_multi_source("8447351005797")
        self.assertEqual(result["source"], "UPCItemDB")
        mock_monster.assert_not_called()

    @patch("taric_lookup.fetch_barcodelookup_product")
    @patch("taric_lookup.fetch_ean_search_product")
    @patch("taric_lookup.fetch_go_upc_product")
    @patch("taric_lookup.fetch_barcode_monster_product")
    @patch("taric_lookup.fetch_upcitemdb_product")
    @patch("taric_lookup.fetch_openfoodfacts_product")
    def test_fetch_product_multi_source_all_fail(self, mock_off, mock_upc, mock_monster, mock_go, mock_es, mock_bl):
        mock_off.return_value = {"source": "OpenFoodFacts", "found": False}
        mock_upc.return_value = {"source": "UPCItemDB", "found": False}
        mock_monster.return_value = {"source": "BarcodeMonster", "found": False}
        mock_go.return_value = {"source": "GoUPC", "found": False}
        mock_es.return_value = {"source": "EANSearch", "found": False}
        mock_bl.return_value = {"source": "BarcodeLookup", "found": False}
        result = fetch_product_multi_source("0000000000000")
        self.assertFalse(result["found"])

    # ------------------------------------------------------------------
    # End-to-end: water barcode 5201005080027 → TARIC 2201
    # ------------------------------------------------------------------

    @patch("taric_lookup.ai_rewrite_to_customs_text", return_value=None)
    @patch("taric_lookup.fetch_product_multi_source")
    def test_resolve_water_barcode_5201005080027(self, mock_multi, _mock_ai):
        """ΑΥΡΑ natural still mineral water should map to TARIC 2201101100."""
        mock_multi.return_value = {
            "source": "OpenFoodFacts",
            "found": True,
            "product_name": "AVRA Natural Mineral Water 500ml",
            "categories": "en:mineral-waters, en:non-carbonated-beverages",
            "brand": "AVRA",
            "description": "Natural still mineral water",
        }
        result = resolve_item("5201005080027", ai_provider="none")
        self.assertEqual(result["barcode"], "5201005080027")
        self.assertTrue(result["valid_ean13"])
        self.assertEqual(result["match"]["hs4"], "2201")
        self.assertEqual(result["match"]["taric_code"], "2201101100")

    # ------------------------------------------------------------------
    # End-to-end: vape barcode 8447351005797 → TARIC 2404
    # ------------------------------------------------------------------

    @patch("taric_lookup.ai_rewrite_to_customs_text", return_value=None)
    @patch("taric_lookup.fetch_product_multi_source")
    def test_resolve_vape_barcode_8447351005797(self, mock_multi, _mock_ai):
        """Bombo Bar vape e-liquid should map to TARIC 2404120000."""
        mock_multi.return_value = {
            "source": "UPCItemDB",
            "found": True,
            "product_name": "Bombo Bar Juice Hyper Boost Pear Ice Flavor Shot",
            "categories": "Electronic Cigarettes",
            "brand": "Bombo",
            "description": "Vape e-liquid flavor shot for electronic cigarette, nicotine-free",
        }
        result = resolve_item("8447351005797", ai_provider="none")
        self.assertEqual(result["barcode"], "8447351005797")
        self.assertTrue(result["valid_ean13"])
        self.assertEqual(result["match"]["hs4"], "2404")
        self.assertEqual(result["match"]["taric_code"], "2404120000")


if __name__ == "__main__":
    unittest.main()

