# barcode-taric

Bidirectional barcode ↔ product description ↔ TARIC code matcher with persistent database.

## Features
- **Bidirectional Search** (2-Way System):
  - **Barcode → Product Info + TARIC Code**: Look up by 13-digit barcode
  - **Product Description → Barcode + TARIC Code**: Full-text search existing database
- **Product Database** with SQLite:
  - Automatically stores all lookups (barcode, product name, description, customs text, TARIC codes)
  - Full-text search (FTS5) on descriptions and product names
  - Export/import database as JSON for backup or sharing
- Single query input (barcode or free-text description)
- Batch input from `.txt`, `.csv`, `.tsv`, `.xlsx`
- Multi-source barcode lookup (tried in order, first hit wins):
  - **OpenFoodFacts** – food & beverage products
  - **UPC ItemDB** – broad product catalogue (free tier, ~100 req/day)
  - **Barcode Monster** – additional fallback
- Rule-based parser for commercial → customs description rewrite
- Optional free AI rewrite via Pollinations (no API key)
- Optional OpenRouter free model if `OPENROUTER_API_KEY` is set via `.env` or environment variables
- New barcode scraping endpoints for `https://go-upc.com/search?q={barcode}`, `https://www.ean-search.org/?q={barcode}` and `https://www.barcodelookup.com/{barcode}`
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

## Run in a new Codespace

1. Open the repository in a fresh Codespace.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies from `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the web UI:
   ```bash
   python web_app.py
   ```
   The Flask server runs in debug mode and will auto-reload when you save changes.
5. Open the browser at:
   ```text
   http://localhost:5000
   ```

If `localhost:5000` is already in use, stop the existing server first or choose a different port by editing `web_app.py` before starting.

## 🔄 Bidirectional 2-Way System

The system supports **bi-directional lookup**:

### Forward Lookup (Barcode → Product + TARIC)
```bash
python taric_lookup.py "5901234123457" --ai-provider none
```
Input: 13-digit barcode  
Output: Product name, barcode, TARIC code, TARIC description

### Reverse Lookup (Description → Barcode + TARIC)
```bash
python taric_lookup.py "Corona Extra beer" --mode description --ai-provider none
```
Input: Product description or name  
Output: Barcode (if available), TARIC code, stored product details

### Auto-Detection (Default Behavior)
```bash
# Auto-detects if input is barcode or description
python taric_lookup.py "5901234123457"        # Recognized as barcode
python taric_lookup.py "cotton shirt"         # Recognized as description
```

## CLI Usage

### Barcode Lookup (Auto-Detected)
```bash
python taric_lookup.py "5901234123457" --ai-provider none
```

### Description Search (Auto-Detected)
```bash
python taric_lookup.py "Ανδρικό βαμβακερό πουκάμισο μακρυμάνικο" --ai-provider none
```

### Explicit Mode Selection
```bash
# Force barcode mode
python taric_lookup.py "5901234123457" --mode barcode --ai-provider pollinations

# Force description mode (search database)
python taric_lookup.py "beer" --mode description --ai-provider none
```

### Batch Processing
```bash
python taric_lookup.py --file /path/to/products.txt --ai-provider pollinations --output taric_output.json
```

### Database Management
```bash
# List all products with complete details (Date/Time, TARIC, Barcode, Description)
python taric_lookup.py --list-db
python taric_lookup.py --view-db    # Alias

# Export database to JSON backup
python taric_lookup.py --export-db

# Import products from JSON
python taric_lookup.py --import-db product_database.json

# Disable database storage for a lookup (one-time queries)
python taric_lookup.py "5901234123457" --no-db --ai-provider none
```

### Database Structure
Each product record in the database contains:
- **⏰ DATE/TIME**: Insertion timestamp (YYYY-MM-DD HH:MM:SS)
- **🏷️ BARCODE**: 13-digit product barcode (if applicable)
- **📦 TARIC CODE**: 10-digit EU TARIC classification code
- **📝 HS4**: 4-digit HS (Harmonized System) code
- **🎯 TARIC DESCRIPTION**: Official TARIC match description
- **📌 PRODUCT NAME**: Commercial product name
- **📄 DESCRIPTION**: Full product description (from source API)
- **🛒 COMMERCIAL TEXT**: Combined commercial description
- **🔧 CUSTOMS TEXT**: Normalized customs/tariff description
- **🔗 SOURCE**: Data source (OpenFoodFacts, API, import, etc.)

### Full-Text Search
The database uses SQLite FTS5 for fast full-text search on:
- Product names
- Descriptions
- Commercial text
- Customs text

### Excel support
For `.xlsx` input install optional dependency:

```bash
pip install openpyxl
```

## Tests

```bash
python -m unittest -v
```
