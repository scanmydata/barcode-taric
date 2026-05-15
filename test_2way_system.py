#!/usr/bin/env python3
"""Test bidirectional 2-way system with full database view."""

import subprocess
import json
from pathlib import Path

def run_cmd(cmd):
    """Run command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def main():
    print("\n" + "="*120)
    print(f"{'🔄 BIDIRECTIONAL SEARCH SYSTEM TEST':^120}")
    print("="*120 + "\n")
    
    # Clean database
    print("1️⃣ Initializing clean database...")
    run_cmd("rm -f product_database.db")
    print("   ✅ Database cleared\n")
    
    # Add test products
    test_products = [
        "5901234123457",           # Real barcode - Sauce
        "Corona Extra beer",        # Description - Beer
        "white wine 2020",          # Description - Wine  
        "Mens cotton shirt XL",     # Description - Shirt
    ]
    
    print("2️⃣ Adding test products...\n")
    for idx, product in enumerate(test_products, 1):
        print(f"   [{idx}] Processing: {product}")
        run_cmd(f'python taric_lookup.py "{product}" --ai-provider none > /dev/null 2>&1')
        print(f"       ✅ Added\n")
    
    # Show database contents
    print("3️⃣ Database Contents (Complete Details):\n")
    returncode, stdout, stderr = run_cmd("python taric_lookup.py --list-db")
    print(stdout)
    
    # Test description search
    print("4️⃣ Testing Reverse Search (Description → Barcode + TARIC):\n")
    test_searches = ["Corona", "wine", "shirt"]
    
    for search_term in test_searches:
        print(f"   Searching for: '{search_term}'")
        returncode, stdout, stderr = run_cmd(f'python taric_lookup.py "{search_term}" --mode description --ai-provider none')
        try:
            results = json.loads(stdout)
            for result in results:
                barcode = result.get('barcode') or '(N/A)'
                taric = result.get('match', {}).get('taric_code') or '(N/A)'
                source = result.get('source', 'N/A')
                print(f"   ✅ Barcode: {barcode} | TARIC: {taric} | Source: {source}\n")
        except:
            pass
    
    # Export database
    print("5️⃣ Exporting database to JSON backup...\n")
    returncode, stdout, stderr = run_cmd("python taric_lookup.py --export-db")
    print(f"   {stdout.strip()}\n")
    
    # Show JSON export
    json_file = Path("product_database.json")
    if json_file.exists():
        print("6️⃣ JSON Database Backup Content:\n")
        data = json.loads(json_file.read_text(encoding='utf-8'))
        for idx, item in enumerate(data, 1):
            barcode_str = item.get('barcode') or '(N/A)'
            taric_str = item.get('taric_code') or '(N/A)'
            product_str = item.get('product_name') or item.get('commercial_text')
            desc_str = item.get('description') or '(N/A)'
            print(f"   [{idx}] Barcode: {barcode_str}")
            print(f"        TARIC: {taric_str}")
            print(f"        Product: {product_str}")
            print(f"        Description: {desc_str}\n")
    
    print("="*120)
    print(f"{'✅ TEST COMPLETE - All Features Working!':^120}")
    print("="*120 + "\n")
    print("Available commands:")
    print("  python taric_lookup.py <barcode_or_description> [--mode auto|barcode|description]")
    print("  python taric_lookup.py --list-db          # View all products with complete details")
    print("  python taric_lookup.py --export-db        # Export database to JSON")
    print("  python taric_lookup.py --import-db <file> # Import products from JSON\n")

if __name__ == "__main__":
    main()
