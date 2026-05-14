#!/usr/bin/env python3
"""Barcode/description to TARIC matcher with free/no-key defaults."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional


OPENFOODFACTS_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
POLLINATIONS_URL = "https://text.pollinations.ai/{prompt}"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass(frozen=True)
class TaricEntry:
    taric_code: str
    hs4: str
    description: str
    keywords: tuple[str, ...]


DEFAULT_TARIC_CATALOG: tuple[TaricEntry, ...] = (
    TaricEntry("2201100000", "2201", "Waters, including natural or artificial mineral waters", ("water", "mineral", "drink")),
    TaricEntry("6105100000", "6105", "Men's shirts of cotton, knitted or crocheted", ("shirt", "mens", "cotton", "garment", "clothing")),
    TaricEntry("8471300000", "8471", "Portable automatic data processing machines", ("laptop", "notebook", "computer", "macbook")),
    TaricEntry("2404120000", "2404", "Products for inhalation without combustion", ("vape", "e-liquid", "electronic cigarette", "liquid")),
)


_TRANSLATIONS = {
    "ανδρ": "mens",
    "βαμβακερ": "cotton",
    "πουκάμισ": "shirt",
    "μακρυμάνικ": "long sleeve",
    "φορητός υπολογιστής": "laptop",
    "υπολογιστής": "computer",
    "νερό": "water",
    "μεταλλικό νερό": "mineral water",
    "υγρό vape": "vape e-liquid",
    "υγρό ηλεκτρονικού τσιγάρου": "vape e-liquid",
    "ηλεκτρονικό τσιγάρο": "electronic cigarette",
}


def _debug(message: str) -> None:
    if os.getenv("BARCODE_TARIC_DEBUG") == "1":
        print(f"[debug] {message}", file=sys.stderr)


def _http_json(url: str, *, timeout: int = 12, method: str = "GET", body: Optional[dict[str, Any]] = None, headers: Optional[dict[str, str]] = None) -> Any:
    payload = None
    req_headers = {"User-Agent": "barcode-taric/1.0"}
    if headers:
        req_headers.update(headers)
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, method=method, data=payload, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_text(url: str, *, timeout: int = 12) -> str:
    req = urllib.request.Request(url=url, headers={"User-Agent": "barcode-taric/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def normalize_to_ean13(code: str) -> Optional[str]:
    digits = re.sub(r"\D", "", code)
    if len(digits) == 13:
        return digits
    if len(digits) == 12:
        checksum = _ean13_checksum(digits)
        return f"{digits}{checksum}"
    if len(digits) == 8:
        return digits.rjust(13, "0")
    return None


def is_valid_ean13(code: str) -> bool:
    if not code.isdigit() or len(code) != 13:
        return False
    return _ean13_checksum(code[:12]) == int(code[-1])


def _ean13_checksum(first12: str) -> int:
    numbers = [int(d) for d in first12]
    total = sum(numbers[i] for i in range(0, 12, 2)) + 3 * sum(numbers[i] for i in range(1, 12, 2))
    return (10 - (total % 10)) % 10


def load_inputs(file_path: Path) -> list[str]:
    suffix = file_path.suffix.lower()
    if suffix == ".txt":
        return [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        values: list[str] = []
        with file_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            for row in reader:
                for col in row:
                    val = col.strip()
                    if val:
                        values.append(val)
        return values

    if suffix in {".xlsx", ".xlsm"}:
        try:
            from openpyxl import load_workbook  # type: ignore
        except ImportError as exc:
            raise ValueError("For Excel input install openpyxl: pip install openpyxl") from exc

        workbook = load_workbook(filename=file_path, read_only=True, data_only=True)
        excel_values: list[str] = []
        for sheet in workbook.worksheets:
            for row in sheet.iter_rows(values_only=True):
                for cell in row:
                    if cell is None:
                        continue
                    value = str(cell).strip()
                    if value:
                        excel_values.append(value)
        return excel_values

    raise ValueError("Unsupported input file type. Use .txt, .csv, .tsv, .xlsx")


def fetch_openfoodfacts_product(barcode: str) -> dict[str, Any]:
    try:
        payload = _http_json(OPENFOODFACTS_URL.format(barcode=urllib.parse.quote(barcode)), timeout=10)
    except TimeoutError:
        return {"source": "OpenFoodFacts", "found": False, "error": "timeout"}
    except urllib.error.URLError:
        return {"source": "OpenFoodFacts", "found": False, "error": "network_error"}
    except json.JSONDecodeError:
        return {"source": "OpenFoodFacts", "found": False, "error": "invalid_response"}

    if payload.get("status") != 1:
        return {"source": "OpenFoodFacts", "found": False}

    product = payload.get("product", {})
    return {
        "source": "OpenFoodFacts",
        "found": True,
        "product_name": product.get("product_name"),
        "brand": product.get("brands"),
        "categories": product.get("categories"),
    }


def parser_rewrite_to_customs_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    for source, target in _TRANSLATIONS.items():
        if source in cleaned:
            cleaned = cleaned.replace(source, target)

    tokens = re.findall(r"[a-z0-9\-]+", cleaned)
    stopwords = {"and", "or", "for", "with", "the", "των", "και", "σε", "με"}
    tokens = [tok for tok in tokens if tok not in stopwords]
    return " ".join(tokens)


def ai_rewrite_to_customs_text(text: str, provider: str = "pollinations") -> Optional[str]:
    prompt = (
        "Rewrite this commercial product text into a concise customs-style description in English. "
        "Return only the description: "
        f"{text}"
    )

    if provider == "none":
        return None

    try:
        if provider == "pollinations":
            encoded = urllib.parse.quote(prompt)
            response = _http_text(POLLINATIONS_URL.format(prompt=encoded), timeout=18).strip()
            return response[:500] if response else None

        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                return None

            payload = {
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
            response = _http_json(
                OPENROUTER_URL,
                method="POST",
                body=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=20,
            )
            return response["choices"][0]["message"]["content"].strip()

    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        _debug(f"AI rewrite failed ({provider}): {exc}")
        return None

    return None


def best_taric_match(customs_text: str, catalog: Iterable[TaricEntry] = DEFAULT_TARIC_CATALOG) -> Optional[TaricEntry]:
    text = f" {customs_text.lower()} "
    best: tuple[int, Optional[TaricEntry]] = (0, None)
    for entry in catalog:
        score = sum(1 for keyword in entry.keywords if f" {keyword.lower()} " in text)
        if score > best[0]:
            best = (score, entry)
    return best[1]


def resolve_item(item: str, *, ai_provider: str = "pollinations") -> dict[str, Any]:
    query = item.strip()
    normalized_barcode = normalize_to_ean13(query)

    source_data: dict[str, Any] = {}
    commercial_text = query
    if normalized_barcode:
        source_data = fetch_openfoodfacts_product(normalized_barcode)
        if source_data.get("found"):
            commercial_text = " ".join(
                str(v) for v in (source_data.get("product_name"), source_data.get("categories"), source_data.get("brand")) if v
            )

    parser_text = parser_rewrite_to_customs_text(commercial_text)
    ai_text = ai_rewrite_to_customs_text(commercial_text, provider=ai_provider)
    customs_text = parser_rewrite_to_customs_text(ai_text) if ai_text else parser_text

    match = best_taric_match(customs_text)

    return {
        "input": query,
        "barcode": normalized_barcode,
        "valid_ean13": is_valid_ean13(normalized_barcode) if normalized_barcode else False,
        "source": source_data or {"source": "direct_input"},
        "commercial_text": commercial_text,
        "customs_text": customs_text,
        "match": {
            "taric_code": match.taric_code if match else None,
            "hs4": match.hs4 if match else None,
            "description": match.description if match else "No confident match",
        },
    }


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Match barcode or product description to TARIC code")
    parser.add_argument("query", nargs="?", help="Single barcode or product description")
    parser.add_argument("--file", type=Path, help="Batch file with inputs (.txt/.csv/.xlsx)")
    parser.add_argument("--ai-provider", choices=["pollinations", "openrouter", "none"], default="pollinations")
    parser.add_argument("--output", type=Path, default=Path("taric_output.json"), help="Output JSON path")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    items: list[str] = []
    if args.query:
        items.append(args.query)
    if args.file:
        try:
            items.extend(load_inputs(args.file))
        except (ValueError, OSError) as exc:
            print(f"Failed to read {args.file}: {exc}", file=sys.stderr)
            return 2

    if not items:
        print("Provide a query or --file", file=sys.stderr)
        return 2

    results = [resolve_item(item, ai_provider=args.ai_provider) for item in items]
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"Saved {len(results)} result(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
