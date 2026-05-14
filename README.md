# barcode-taric

Minimal CLI + GUI for matching barcodes or product descriptions to TARIC codes.

## Features
- Single query input (barcode or free-text description)
- Batch input from `.txt`, `.csv`, `.tsv`, `.xlsx`
- Multi-source barcode lookup (tried in order, first hit wins):
  - **OpenFoodFacts** – food & beverage products
  - **UPC ItemDB** – broad product catalogue (free tier, ~100 req/day)
  - **Barcode Monster** – additional fallback
- Rule-based parser for commercial → customs description rewrite
- Optional free AI rewrite via Pollinations (no API key)
- Optional OpenRouter free model if `OPENROUTER_API_KEY` is set
- Expanded TARIC catalog with correct 10-digit codes (food, beverages, vaping, clothing, electronics, cosmetics, pharma)
- Unified JSON output with normalized input, source context, customs text and TARIC match
- **Tkinter GUI** for interactive single/batch lookups and JSON export

## GUI

```bash
python gui.py
```

Add barcodes or descriptions one-by-one (press Enter or click **Add**) or load a batch file with **Load File…**.  
Choose an AI provider, click **🔍 Search TARIC Codes** and results appear in the table.  
Use **Export JSON…** to save the full result set.

## CLI Usage

```bash
python taric_lookup.py "Ανδρικό βαμβακερό πουκάμισο μακρυμάνικο" --ai-provider none
```

```bash
python taric_lookup.py --file /path/to/products.txt --ai-provider pollinations --output taric_output.json
```

### Excel support
For `.xlsx` input install optional dependency:

```bash
pip install openpyxl
```

## Tests

```bash
python -m unittest -v
```
