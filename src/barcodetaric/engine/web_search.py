"""Πραγματικά Google results σε πολλαπλά επίπεδα (tiers).

  1. googlesearch-python  (δωρεάν scraping, τίτλος+περιγραφή+URL)
  2. Google Custom Search JSON API  (επίσημο, 100/μέρα δωρεάν, αν υπάρχει key+cse_id)
  3. DuckDuckGo HTML  (fallback, χωρίς key/όρια)

Επιστρέφει λίστα από dicts {title, url, snippet}. Τα snippets τροφοδοτούν το AI
για (α) αντιπαραβολή barcode<->περιγραφής και (β) αναγνώριση τι είναι το προϊόν.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.parse
from typing import Any

from ..config import SETTINGS
from .http_util import BROWSER_UA, debug, http_json, http_text, strip_tags


def _via_googlesearch(query: str, limit: int) -> list[dict[str, str]]:
    try:
        from googlesearch import search  # type: ignore
    except ImportError:
        debug("googlesearch-python not installed")
        return []
    results: list[dict[str, str]] = []
    try:
        for item in search(query, num_results=limit, advanced=True, lang="el"):
            results.append({
                "title": getattr(item, "title", "") or "",
                "url": getattr(item, "url", "") or "",
                "snippet": getattr(item, "description", "") or "",
            })
    except Exception as exc:  # noqa: BLE001 - η βιβλιοθήκη ρίχνει διάφορα σε rate-limit
        debug(f"googlesearch failed: {exc}")
    return results


def _via_google_cse(query: str, limit: int) -> list[dict[str, str]]:
    api_key = SETTINGS.get("google_cse_api_key")
    cse_id = SETTINGS.get("google_cse_id")
    if not api_key or not cse_id:
        return []
    url = (
        "https://www.googleapis.com/customsearch/v1?"
        + urllib.parse.urlencode({"key": api_key, "cx": cse_id, "q": query, "num": min(limit, 10)})
    )
    try:
        payload = http_json(url, timeout=15)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        debug(f"Google CSE failed: {exc}")
        return []
    items = payload.get("items") or []
    return [{"title": it.get("title", ""), "url": it.get("link", ""),
             "snippet": it.get("snippet", "")} for it in items[:limit]]


def _via_duckduckgo(query: str, limit: int) -> list[dict[str, str]]:
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    try:
        html_text = http_text(url, timeout=15, headers={"User-Agent": BROWSER_UA})
    except (urllib.error.URLError, TimeoutError):
        return []
    results: list[dict[str, str]] = []
    blocks = re.findall(r'<div[^>]*class=["\']result[^"\']*["\'][^>]*>(.*?)</div>\s*</div>',
                        html_text, re.S | re.I)
    for block in blocks[:limit]:
        title_m = re.search(r'class=["\']result__a["\'][^>]*>(.*?)</a>', block, re.S | re.I)
        snip_m = re.search(r'class=["\']result__snippet["\'][^>]*>(.*?)</a>', block, re.S | re.I)
        url_m = re.search(r'href=["\'](https?://[^"\']+)["\']', block, re.I)
        results.append({
            "title": strip_tags(title_m.group(1)) if title_m else "",
            "url": url_m.group(1) if url_m else "",
            "snippet": strip_tags(snip_m.group(1)) if snip_m else "",
        })
    return results


_TIERS = {
    "googlesearch": _via_googlesearch,
    "google_cse": _via_google_cse,
    "duckduckgo": _via_duckduckgo,
}


def search_web(query: str, *, limit: int = 6) -> list[dict[str, str]]:
    """Δοκιμάζει τα tiers με τη σειρά ρυθμίσεων· επιστρέφει τα πρώτα αποτελέσματα."""
    order = SETTINGS.get("web_search_order") or ["googlesearch", "google_cse", "duckduckgo"]
    for name in order:
        fn = _TIERS.get(name)
        if fn is None:
            continue
        results = fn(query, limit)
        if results:
            debug(f"web_search via {name}: {len(results)} results")
            return results
    return []


def context_text(query: str, *, limit: int = 6) -> str:
    """Μονο-string context (τίτλος - snippet ανά γραμμή) για prompts του AI."""
    items = search_web(query, limit=limit)
    lines = []
    for it in items:
        line = " - ".join(p for p in (it.get("title", ""), it.get("snippet", "")) if p)
        if line:
            lines.append(line)
    return "\n".join(lines)
