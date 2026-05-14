# barcode-taric

Minimal CLI for matching barcode or product description to a TARIC code.

## Features
- Single query input (barcode or free-text description)
- Batch input from `.txt`, `.csv`, `.tsv`, `.xlsx`
- Free/no-key defaults:
  - OpenFoodFacts for barcode product metadata
  - Rule-based parser for commercial -> customs description rewrite
  - Optional free AI rewrite via Pollinations (no API key)
  - Optional OpenRouter free model if `OPENROUTER_API_KEY` is set
- Unified JSON output with normalized input, source context, customs text and TARIC match

## Usage

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
