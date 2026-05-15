#!/usr/bin/env python3
"""Quick barcode lookup helper with external API integration."""

import sys
import json
import urllib.request
import urllib.error
from taric_lookup import resolve_item

def lookup_barcode(barcode):
    """Lookup barcode info from APIs and find TARIC match."""
    print(f"\n🔍 Searching barcode: {barcode}")
    print("=" * 60)
    
    # Try UPC ItemDB API
    try:
        url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={barcode}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            if data.get('items'):
                item = data['items'][0]
                title = item.get('title', 'N/A')
                category = item.get('category', 'N/A')
                brand = item.get('brand', 'N/A')
                price = item.get('offers', [{}])[0].get('price', 'N/A')
                
                print(f"✅ Product Found:")
                print(f"   Title: {title}")
                print(f"   Category: {category}")
                print(f"   Brand: {brand}")
                print(f"   Price: ${price}")
                
                # Now lookup TARIC for this product using AI
                lookup_text = f"{title} {category} {brand}"
                result = resolve_item(lookup_text, ai_provider="openrouter")
                
                print(f"\n📦 TARIC Classification:")
                if result.get('match') and result['match'].get('taric_code'):
                    print(f"   TARIC Code: {result['match']['taric_code']}")
                    print(f"   HS4: {result['match']['hs4']}")
                    print(f"   Description: {result['match']['description']}")
                else:
                    print(f"   ❌ No TARIC match found")
                    print(f"   Try: python taric_lookup.py \"{title}\"")
                
                print("=" * 60)
                return result
            else:
                print(f"❌ Barcode not found in UPC ItemDB")
    except urllib.error.URLError as e:
        print(f"⚠️ API Error: {e}")
    except Exception as e:
        print(f"⚠️ Error: {e}")
    
    print("=" * 60)
    return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python quick_lookup.py <barcode> [<barcode2> ...]")
        print("Example: python quick_lookup.py 92399558859 5201005080027")
        sys.exit(1)
    
    for barcode in sys.argv[1:]:
        lookup_barcode(barcode)
