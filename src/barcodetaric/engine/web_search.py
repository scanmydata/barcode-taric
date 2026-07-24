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


def _via_openserp(query: str, limit: int) -> list[dict[str, str]]:
    """Πραγματικά αποτελέσματα Google/άλλων μηχανών μέσω τοπικού OpenSERP server.

    Το OpenSERP (github.com/karust/openserp) τρέχει τοπικά έναν headless browser και
    δίνει αποτελέσματα ΧΩΡΙΣ API key, παρακάμπτοντας το μπλοκάρισμα του απλού
    scraping. Ο χρήστης το ξεκινά ξεχωριστά:
        docker run --rm -p 127.0.0.1:7000:7000 karust/openserp:latest serve -a 0.0.0.0 -p 7000
    Αν ο server δεν τρέχει, η κλήση αποτυγχάνει σιωπηλά και πέφτουμε στο επόμενο tier.
    """
    base = (SETTINGS.get("openserp_url") or "http://127.0.0.1:7000").rstrip("/")
    engine = (SETTINGS.get("openserp_engine") or "google").strip().lower()
    try:
        timeout = int(SETTINGS.get("openserp_timeout") or 45)
    except (TypeError, ValueError):
        timeout = 45
    url = base + f"/{engine}/search?" + urllib.parse.urlencode(
        {"text": query, "lang": "EN", "limit": min(limit, 100), "format": "json"}
    )
    try:
        # Ο headless browser του OpenSERP είναι αργός (ειδικά στο πρώτο query),
        # γι' αυτό γενναίο timeout· αν ο server δεν τρέχει, σκάει αμέσως (refused).
        payload = http_json(url, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        debug(f"OpenSERP failed (server running?): {exc}")
        return []
    items = payload if isinstance(payload, list) else (payload.get("results") or payload.get("items") or [])
    out: list[dict[str, str]] = []
    for it in items[:limit]:
        if not isinstance(it, dict):
            continue
        out.append({"title": str(it.get("title", "")),
                    "url": str(it.get("url", "") or it.get("link", "")),
                    "snippet": str(it.get("snippet", "") or it.get("description", ""))})
    return out


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
    "openserp": _via_openserp,
    "googlesearch": _via_googlesearch,
    "google_cse": _via_google_cse,
    "duckduckgo": _via_duckduckgo,
}


def search_web(query: str, *, limit: int = 6) -> list[dict[str, str]]:
    """Δοκιμάζει τα tiers με τη σειρά ρυθμίσεων· επιστρέφει τα πρώτα αποτελέσματα."""
    order = SETTINGS.get("web_search_order") or ["openserp", "googlesearch", "google_cse", "duckduckgo"]
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


def _dedup_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for it in items:
        key = (it.get("title", "") + "|" + it.get("snippet", "")).strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def gather_context(*, barcode: str = "", name: str = "", brand: str = "",
                   limit: int = 5) -> dict[str, Any]:
    """Παράλληλο cross-check: ψάχνει ΤΑΥΤΟΧΡΟΝΑ για το barcode ΚΑΙ για την περιγραφή.

    Επιστρέφει {"barcode_hits", "name_hits", "text"} όπου text είναι ενοποιημένο
    context (τίτλος - snippet) για το AI. Οι δύο άξονες (barcode vs όνομα)
    διασταυρώνονται ώστε το AI να επιβεβαιώσει ΤΙ είναι πραγματικά το προϊόν.
    """
    from concurrent.futures import ThreadPoolExecutor

    queries: list[tuple[str, str]] = []
    if barcode:
        queries.append(("barcode", barcode))
        queries.append(("barcode", f"{barcode} προϊόν product"))
    if name:
        queries.append(("name", name if not brand else f"{brand} {name}"))

    results: dict[str, list[dict[str, str]]] = {"barcode": [], "name": []}
    if queries:
        with ThreadPoolExecutor(max_workers=min(4, len(queries))) as pool:
            futures = {pool.submit(search_web, q, limit=limit): axis for axis, q in queries}
            for future in futures:
                axis = futures[future]
                try:
                    results[axis].extend(future.result())
                except Exception as exc:  # noqa: BLE001
                    debug(f"gather_context query failed ({axis}): {exc}")

    barcode_hits = _dedup_items(results["barcode"])[: limit + 2]
    name_hits = _dedup_items(results["name"])[:limit]

    def _fmt(items: list[dict[str, str]]) -> str:
        lines = []
        for it in items:
            line = " - ".join(p for p in (it.get("title", ""), it.get("snippet", "")) if p)
            if line:
                lines.append(line)
        return "\n".join(lines)

    text_parts = []
    if barcode_hits:
        text_parts.append("Αποτελέσματα web για το barcode:\n" + _fmt(barcode_hits))
    if name_hits:
        text_parts.append("Αποτελέσματα web για την ονομασία:\n" + _fmt(name_hits))

    return {"barcode_hits": barcode_hits, "name_hits": name_hits,
            "text": "\n\n".join(text_parts)}
