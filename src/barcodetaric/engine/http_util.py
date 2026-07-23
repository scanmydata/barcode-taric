"""Ελαφριά HTTP utilities (stdlib urllib) + text normalisation helpers."""

from __future__ import annotations

import html
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

USER_AGENT = "barcodetaric/1.0"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def debug(message: str) -> None:
    if os.getenv("BARCODETARIC_DEBUG") == "1":
        print(f"[debug] {message}", file=sys.stderr)
    try:
        from ..logs import debug as _log_debug
        _log_debug(message)
    except Exception:  # noqa: BLE001 - το logging δεν πρέπει ποτέ να σπάει τη ροή
        pass


def http_json(url: str, *, timeout: int = 12, method: str = "GET",
              body: Optional[dict[str, Any]] = None,
              headers: Optional[dict[str, str]] = None) -> Any:
    payload = None
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, method=method, data=payload, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def http_text(url: str, *, timeout: int = 12, headers: Optional[dict[str, str]] = None) -> str:
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url=url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def unescape_text(value: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", value.strip()))


def strip_tags(value: str) -> str:
    return unescape_text(re.sub(r"<[^>]+>", " ", value))


def normalize_for_matching(text: str) -> str:
    lowered = text.lower()
    without = "".join(c for c in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(c))
    normalized = re.sub(r"[^a-z0-9\s\-]", " ", without)
    return re.sub(r"\s+", " ", normalized).strip()


def contains_greek(text: Optional[str]) -> bool:
    return bool(text and re.search("[Ͱ-Ͽἀ-῿]", text))


# Ελαφρύ stemming ώστε ενικός/πληθυντικός & κλίσεις να συγκλίνουν (νερό/νερά, water/waters).
_GREEK_SUFFIXES = ("οντας", "ουν", "εις", "ους", "ων", "ος", "ου", "οι", "ες", "ας",
                    "ης", "α", "ο", "ε", "η", "ι", "υ", "ς")


def stem_token(token: str) -> str:
    """Δέχεται token ήδη πεζό & χωρίς τόνους (a-z ή α-ω). Επιστρέφει ρίζα."""
    t = token
    if t and t[0].isascii():  # αγγλικό/λατινικό
        if t.endswith("ies") and len(t) > 5:
            t = t[:-3] + "y"
        elif t.endswith("es") and len(t) > 5:
            t = t[:-2]
        elif t.endswith("s") and not t.endswith("ss") and len(t) > 4:
            t = t[:-1]
        return t
    for suf in _GREEK_SUFFIXES:  # ελληνικό
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)]
    return t


def contains_latin(text: Optional[str]) -> bool:
    return bool(text and re.search(r"[A-Za-z]", text))
