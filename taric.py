#!/usr/bin/env python3
"""
TARIC Data Downloader and Lookup Tool

This script can:
1. Download TARIC data from EU sources (when available)
2. Look up TARIC codes for barcodes or product descriptions
3. Use the local full_taric_catalog.py for offline lookups
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
import urllib.parse
import time
from pathlib import Path

# Try to import the local catalog
try:
    from full_taric_catalog import FULL_TARIC_CATALOG
    HAS_CATALOG = True
except ImportError:
    HAS_CATALOG = False

# Official EU data sources
DATA_EUROPA_API = "https://data.europa.eu/api/hub/search/datasets/eu-customs-tariff-taric"
EUROPA_CIRCA_URL = "https://circabc.europa.eu/ui/group/71c4e6b8-3853-4d80-b73b-41e5e14e66d7/library/2148dfe4-37c3-4a6b-9f63-3ebf06f279f8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def normalize_text(text):
    """Normalize text for matching."""
    import unicodedata
    text = text.lower().strip()
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text):
    """Tokenize text for matching."""
    return re.findall(r"[a-z0-9\-]+", text.lower())


def best_taric_match(query, catalog=None):
    """Find the best TARIC match for a query string."""
    if catalog is None:
        if not HAS_CATALOG:
            return None
        catalog = FULL_TARIC_CATALOG
    
    normalized_query = normalize_text(query)
    query_tokens = set(tokenize(normalized_query))
    text = f" {normalized_query} "
    
    best_score = 0
    best_match = None
    
    for entry in catalog:
        score = 0
        normalized_desc = normalize_text(entry.description)
        
        for keyword in entry.keywords:
            normalized_kw = normalize_text(keyword)
            kw_tokens = set(tokenize(normalized_kw))
            
            if f" {normalized_kw} " in text:
                score += 4 + len(kw_tokens)
            else:
                overlap = len(query_tokens.intersection(kw_tokens))
                score += overlap
        
        # Special handling for nicotine vs non-nicotine vape products
        vaping_keywords = {"vape", "eliquid", "liquid", "ecig", "ecigarette", "puff", "inhalation", "juice"}
        has_vaping_context = bool(query_tokens.intersection(vaping_keywords))
        
        if "nicotine" in query_tokens and has_vaping_context:
            if "with nicotine" in normalized_desc:
                score += 5
            if "without nicotine" in normalized_desc or "no nicotine" in normalized_desc:
                score += 5
        
        if score > best_score:
            best_score = score
            best_match = entry
    
    return best_match


def fetch_with_retry(url, max_retries=3, timeout=30):
    """Fetch URL with retry logic and proper headers."""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8')
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                print(f"  Attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(2 ** attempt)
            else:
                raise


def lookup_taric(query):
    """Look up TARIC code for a query (barcode or description)."""
    # Check if it's a barcode (13 digits)
    digits = re.sub(r'\D', '', query)
    if len(digits) == 13:
        print(f"\n[SEARCH] Looking up barcode: {query}")
        # For barcodes, we would need to fetch product info first
        # This is handled by the web app's resolve_item function
        print("   For barcode lookups, please use the web interface at http://localhost:5000")
        print("   or use: python taric_lookup.py " + query)
        return None
    
    # For descriptions, use local matching
    print(f"\n[SEARCH] Looking up description: {query}")
    
    if not HAS_CATALOG:
        print("   [ERROR] Local TARIC catalog not available")
        return None
    
    match = best_taric_match(query)
    
    if match:
        print(f"   [OK] TARIC Code: {match.taric_code}")
        print(f"   [HS4] HS4: {match.hs4}")
        print(f"   [DESC] Description: {match.description}")
        return match
    else:
        print("   [ERROR] No matching TARIC code found")
        return None


def download_from_data_europa():
    """Download TARIC data from data.europa.eu API."""
    print("[INFO] Attempting to fetch from data.europa.eu...")
    
    try:
        data = json.loads(fetch_with_retry(DATA_EUROPA_API))
        results = data.get('results', [])
        
        if not results:
            print("  [ERROR] No results found in data.europa.eu API response")
            return None
            
        dataset = results[0]
        print(f"  [INFO] Found dataset: {dataset.get('title', 'Unknown')}")
        
        # Look for download resources
        resources = dataset.get('resources', [])
        for resource in resources:
            format_type = resource.get('format', '').lower()
            if format_type in ['csv', 'xlsx', 'json', 'xml']:
                download_url = resource.get('download_url') or resource.get('url')
                if download_url:
                    print(f"  [INFO] Found {format_type.upper()} resource")
                    return download_url
        
        print("  [WARN] No suitable download format found")
        return None
        
    except Exception as e:
        print(f"  [ERROR] Error fetching from data.europa.eu: {e}")
        return None


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("=" * 60)
        print("TARIC Data Downloader & Lookup Tool")
        print("=" * 60)
        print()
        print("Usage:")
        print("  python taric.py <barcode_or_description>  - Look up TARIC code")
        print("  python taric.py --download                - Download TARIC data")
        print()
        print("Examples:")
        print('  python taric.py "natural mineral water"')
        print('  python taric.py "8447351005797"')
        print("  python taric.py --download")
        print()
        
        if HAS_CATALOG:
            print(f"[INFO] Local catalog has {len(FULL_TARIC_CATALOG)} entries")
        else:
            print("[WARN] No local catalog available")
        
        return 0
    
    if sys.argv[1] == '--download':
        print("=" * 60)
        print("TARIC Data Downloader")
        print("=" * 60)
        print()
        
        # Try to download from data.europa.eu
        download_url = download_from_data_europa()
        
        if download_url:
            print(f"\n[URL] Download URL: {download_url}")
            print("   Use a browser or wget/curl to download the file")
        else:
            print("\n[WARN] EU data sources are currently unavailable.")
            print("   The local catalog (full_taric_catalog.py) has 114+ entries.")
            print("   Use 'python taric_lookup.py <query>' for lookups.")
        
        return 0 if download_url else 1
    
    # Look up TARIC code
    query = " ".join(sys.argv[1:])
    lookup_taric(query)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())