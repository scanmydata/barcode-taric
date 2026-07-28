"""Πραγματικά web results σε πολλαπλά επίπεδα (tiers).

  1. searxng          (self-host ή public SearXNG instance, JSON API — αξιόπιστο, χωρίς blocks)
  2. googlesearch-python  (δωρεάν scraping, τίτλος+περιγραφή+URL)
  3. Google Custom Search JSON API  (επίσημο, 100/μέρα δωρεάν, αν υπάρχει key+cse_id)
  4. DuckDuckGo HTML  (fallback, χωρίς key/όρια)

Επιστρέφει λίστα από dicts {title, url, snippet}. Τα snippets τροφοδοτούν το AI
για (α) αντιπαραβολή barcode<->περιγραφής και (β) αναγνώριση τι είναι το προϊόν.

SearXNG (github.com/searxng/searxng) είναι meta-search engine που συγκεντρώνει
δεκάδες πηγές και εκθέτει JSON API (`/search?q=...&format=json`). Το ίδιο endpoint
χρησιμοποιεί και το mcp-searxng (github.com/ihor-sokoliuk/mcp-searxng). Ρύθμισε το
`searxng_url` στις ρυθμίσεις (public instance ή τοπικό `http://127.0.0.1:8888`).
Πολλά public instances κλείνουν το JSON format· για σταθερότητα προτείνεται self-host.
"""

from __future__ import annotations

import re
import unicodedata
import urllib.error
import urllib.parse
from typing import Any

from ..config import SETTINGS
from .http_util import BROWSER_UA, debug, http_json, http_text, strip_tags


def _via_searxng(query: str, limit: int) -> list[dict[str, str]]:
    base = (SETTINGS.get("searxng_url") or "").strip()
    if not base:
        return []
    url = base.rstrip("/") + "/search?" + urllib.parse.urlencode({
        "q": query, "format": "json", "language": "el", "safesearch": "0",
    })
    try:
        payload = http_json(url, timeout=15, headers={"User-Agent": BROWSER_UA})
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        debug(f"SearXNG failed: {exc}")
        return []
    items = payload.get("results") or []
    out = []
    for it in items[:limit]:
        out.append({
            "title": it.get("title", "") or "",
            "url": it.get("url", "") or "",
            "snippet": it.get("content", "") or "",
        })
    return out


_HEADLESS_DRIVER = None  # cache του Selenium driver (ακριβό να ανοίγει κάθε φορά)


def _headless_driver():
    """Lazy, cached headless Chrome μέσω Selenium. None αν λείπει selenium/Chrome."""
    global _HEADLESS_DRIVER
    if _HEADLESS_DRIVER is not None:
        return _HEADLESS_DRIVER
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        debug("selenium not installed (pip install selenium) — headless tier ανενεργό")
        return None
    try:
        opts = Options()
        # «new» headless + anti-automation flags ώστε να μη σημαδεύεται εύκολα ως bot.
        if not SETTINGS.get("headless_headed"):   # true = ορατό παράθυρο (λιγότερο detectable)
            opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1280,900")
        opts.add_argument("--lang=el-GR")
        opts.add_argument(f"--user-agent={BROWSER_UA}")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        binary = (SETTINGS.get("chrome_binary") or "").strip()
        if binary:
            opts.binary_location = binary
        # Χρήση του πραγματικού προφίλ Chrome (cookies/consent/login) -> λιγότερο anti-bot.
        # ΠΡΟΣΟΧΗ: το Chrome πρέπει να είναι ΚΛΕΙΣΤΟ αλλιώς το user-data-dir είναι κλειδωμένο.
        user_dir = (SETTINGS.get("chrome_user_data_dir") or "").strip()
        if user_dir:
            opts.add_argument(f"--user-data-dir={user_dir}")
            profile = (SETTINGS.get("chrome_profile") or "").strip()
            if profile:
                opts.add_argument(f"--profile-directory={profile}")
        driver = webdriver.Chrome(options=opts)  # Selenium Manager βρίσκει το chromedriver
        driver.set_page_load_timeout(25)
        # κρύψε το navigator.webdriver flag (βασικό tell για bot detection)
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            })
        except Exception:  # noqa: BLE001 - δεν είναι κρίσιμο
            pass
        _HEADLESS_DRIVER = driver
        return driver
    except Exception as exc:  # noqa: BLE001 - webdriver/driver init ρίχνει διάφορα
        debug(f"headless Chrome init failed: {exc}")
        return None


def _via_headless(query: str, limit: int) -> list[dict[str, str]]:
    """Πραγματικό headless Chrome στη Google (εκτελεί JS) — παρακάμπτει το block στο scraping."""
    driver = _headless_driver()
    if driver is None:
        return []
    from urllib.parse import quote_plus
    from selenium.webdriver.common.by import By
    url = f"https://www.google.com/search?q={quote_plus(query)}&hl=el&num={min(limit + 3, 15)}"
    try:
        driver.get(url)
    except Exception as exc:  # noqa: BLE001
        debug(f"headless get failed: {exc}")
        return []

    # Google EU consent wall: πάτα «Αποδοχή όλων» αν εμφανιστεί.
    try:
        for xp in ("//button[.//div[contains(text(),'Αποδοχή')]]",
                   "//button[contains(.,'Accept all')]",
                   "//button[contains(.,'Αποδοχή όλων')]"):
            btns = driver.find_elements(By.XPATH, xp)
            if btns:
                btns[0].click()
                import time as _t; _t.sleep(1.0)
                driver.get(url)
                break
    except Exception:  # noqa: BLE001
        pass

    # Bot-detection: η Google ανακατευθύνει στο /sorry (reCAPTCHA) όταν «μυρίζεται» automation.
    if "/sorry" in driver.current_url or "recaptcha" in driver.page_source.lower():
        debug("headless: Google /sorry (bot-detection) — δες SearXNG/DuckDuckGo αντ' αυτού")
        return []

    # Περίμενε να render-άρει (JS) τα οργανικά αποτελέσματα πριν το parsing.
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#search h3")))
    except Exception:  # noqa: BLE001 - συνέχισε· ίσως λίγα/καθόλου αποτελέσματα
        import time as _t; _t.sleep(1.0)

    out: list[dict[str, str]] = []
    try:
        blocks = driver.find_elements(By.CSS_SELECTOR, "div.MjjYud") or \
            driver.find_elements(By.CSS_SELECTOR, "div.tF2Cxc") or \
            driver.find_elements(By.CSS_SELECTOR, "div.g")
        for b in blocks:
            try:
                a = b.find_element(By.CSS_SELECTOR, "a[href^='http']")
                h3 = b.find_elements(By.CSS_SELECTOR, "h3")
                if not h3:
                    continue
                url_v = a.get_attribute("href") or ""
                title = h3[0].text.strip()
                snippet = ""
                for sel in ("div.VwiC3b", "div[data-sncf]", "div.kb0PBd"):
                    els = b.find_elements(By.CSS_SELECTOR, sel)
                    if els and els[0].text.strip():
                        snippet = els[0].text.strip()
                        break
                if title and url_v:
                    out.append({"title": title, "url": url_v, "snippet": snippet})
                if len(out) >= limit:
                    break
            except Exception:  # noqa: BLE001 - stale/missing element σε ένα block
                continue
    except Exception as exc:  # noqa: BLE001
        debug(f"headless parse failed: {exc}")
    return out


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


def _via_searxng(query: str, limit: int) -> list[dict[str, str]]:
    """Μετα-μηχανή SearXNG (self-hosted) μέσω JSON API — πολλαπλές μηχανές μαζί.

    Ιδανικό για το μηχάνημα που τρέχει το τοπικό LLM (ollama): μία αναζήτηση χτυπά
    πολλές μηχανές ταυτόχρονα, χωρίς API key, χωρίς rate-limit της Google. Απαιτεί
    ενεργό `format: json` στο settings.yml του SearXNG. Χωρίς `searxng_url` -> skip.
    """
    base = (SETTINGS.get("searxng_url") or "").strip().rstrip("/")
    if not base:
        return []
    try:
        timeout = int(SETTINGS.get("searxng_timeout") or 15)
    except (TypeError, ValueError):
        timeout = 15
    url = base + "/search?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "language": "en", "safesearch": "0"}
    )
    try:
        payload = http_json(url, timeout=timeout, headers={"Accept": "application/json"})
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        debug(f"SearXNG failed (running? json enabled?): {exc}")
        return []
    items = payload.get("results") or [] if isinstance(payload, dict) else []
    out: list[dict[str, str]] = []
    for it in items[:limit]:
        if not isinstance(it, dict):
            continue
        out.append({"title": str(it.get("title", "")),
                    "url": str(it.get("url", "")),
                    "snippet": strip_tags(str(it.get("content", "") or it.get("snippet", "")))})
    return out


def _via_brave(query: str, limit: int) -> list[dict[str, str]]:
    """Brave Search API — επίσημο, γρήγορο, δομημένο JSON, ανεξάρτητο index.

    Δωρεάν tier: ~2000 queries/μήνα με key (dashboard της Brave). Πολύ πιο αξιόπιστο
    & γρήγορο από το scraping της Google/DDG. Χωρίς key -> σιωπηλά skip.
    """
    api_key = SETTINGS.get("brave_api_key")
    if not api_key:
        return []
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
        {"q": query, "count": min(limit, 20)}
    )
    try:
        payload = http_json(url, timeout=10, headers={
            "Accept": "application/json", "X-Subscription-Token": api_key})
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        debug(f"Brave search failed: {exc}")
        return []
    results = ((payload.get("web") or {}).get("results")) or []
    out: list[dict[str, str]] = []
    for it in results[:limit]:
        if not isinstance(it, dict):
            continue
        out.append({"title": str(it.get("title", "")),
                    "url": str(it.get("url", "")),
                    "snippet": strip_tags(str(it.get("description", "")))})
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
    "searxng": _via_searxng,
    "openserp": _via_openserp,
    "brave": _via_brave,
    "googlesearch": _via_googlesearch,
    "google_cse": _via_google_cse,
    "headless": _via_headless,
    "duckduckgo": _via_duckduckgo,
}

# searxng (αν self-hosted) & duckduckgo = γρήγορα/αξιόπιστα -> πρώτα. headless = πραγματικό
# Chrome στη Google, ισχυρό fallback αλλά αργό (~4s) + η Google το rate-limit-άρει με CAPTCHA
# (/sorry) σε επαναλαμβανόμενα queries· γι' αυτό δεν είναι πρώτο. Άλλαξέ το αν θες Google-first.
_DEFAULT_ORDER = ["searxng", "duckduckgo", "headless", "googlesearch", "google_cse"]


def search_web(query: str, *, limit: int = 6) -> list[dict[str, str]]:
    """Δοκιμάζει τα tiers με τη σειρά ρυθμίσεων· επιστρέφει τα πρώτα αποτελέσματα."""
<<<<<<< HEAD
    order = SETTINGS.get("web_search_order") or ["searxng", "openserp", "brave", "google_cse", "duckduckgo", "googlesearch"]
=======
    order = SETTINGS.get("web_search_order") or _DEFAULT_ORDER
>>>>>>> b69f1c064e06f3062b3591fa58b396eb91ebe117
    for name in order:
        fn = _TIERS.get(name)
        if fn is None:
            continue
        results = fn(query, limit)
        if results:
            debug(f"web_search via {name}: {len(results)} results")
            return results
    return []


def test_tiers(query: str = "coca cola 330ml") -> list[tuple[str, bool, str]]:
    """Debugger: δοκιμάζει κάθε tier ξεχωριστά -> (name, ok, μήνυμα/#αποτελέσματα)."""
    order = SETTINGS.get("web_search_order") or _DEFAULT_ORDER
    out: list[tuple[str, bool, str]] = []
    for name in order:
        fn = _TIERS.get(name)
        if fn is None:
            out.append((name, False, "άγνωστο tier"))
            continue
        if name == "searxng" and not (SETTINGS.get("searxng_url") or "").strip():
            out.append((name, False, "δεν έχει οριστεί searxng_url"))
            continue
        if name == "google_cse" and not (SETTINGS.get("google_cse_api_key") and SETTINGS.get("google_cse_id")):
            out.append((name, False, "λείπει key/cse_id"))
            continue
        if name == "headless":
            try:
                import selenium  # noqa: F401
            except ImportError:
                out.append((name, False, "selenium μη εγκατεστημένο"))
                continue
        try:
            res = fn(query, 5)
            out.append((name, bool(res), f"{len(res)} αποτελέσματα" if res else "κενό"))
        except Exception as exc:  # noqa: BLE001
            out.append((name, False, f"{type(exc).__name__}: {str(exc)[:60]}"))
    return out


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


# Λέξεις που δεν κουβαλούν ταυτότητα προϊόντος (για το corroboration score).
_GENERIC_TOKENS = {
    "the", "and", "for", "with", "product", "products", "buy", "online", "price",
    "shop", "store", "barcode", "ean", "upc", "gtin", "και", "με", "για", "προϊόν",
    "προϊον", "τιμη", "τιμή", "αγορα", "αγορά",
}


def _fold(text: str) -> str:
    """Πεζά + αφαίρεση τόνων, ΚΡΑΤΩΝΤΑΣ ελληνικά ΚΑΙ λατινικά (για cross-check EL/EN)."""
    lowered = (text or "").lower()
    stripped = "".join(c for c in unicodedata.normalize("NFKD", lowered)
                       if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9α-ω\s]", " ", stripped)).strip()


def name_corroboration(name: str, items: list[dict[str, str]]) -> float:
    """Πόσο επιβεβαιώνεται μια υποψήφια ονομασία από τα web αποτελέσματα (0..1).

    Χωρίς AI: μετρά το ποσοστό των διακριτικών λέξεων της ονομασίας που εμφανίζονται
    στους τίτλους/snippets. Χρησιμεύει ως δικλείδα ΟΤΑΝ το LLM δεν είναι διαθέσιμο —
    αν η ονομασία δεν βρίσκεται πουθενά στα αποτελέσματα, μάλλον είναι λάθος/junk.
    """
    from .http_util import stem_token

    tokens = {stem_token(t) for t in _fold(name).split()
              if len(t) > 2 and t not in _GENERIC_TOKENS}
    if not tokens:
        return 0.0
    haystack = " ".join(_fold(f"{it.get('title', '')} {it.get('snippet', '')}") for it in items)
    hay_tokens = {stem_token(t) for t in haystack.split()}
    hit = sum(1 for t in tokens if _match_token(t, hay_tokens))
    return hit / len(tokens)


def _match_token(token: str, haystack: set[str]) -> bool:
    if token in haystack:
        return True
    # prefix-aware (ενικός/πληθυντικός, κλίσεις που ξεφεύγουν του light stemmer)
    if len(token) >= 4:
        return any(len(h) >= 4 and (h.startswith(token) or token.startswith(h)) for h in haystack)
    return False
