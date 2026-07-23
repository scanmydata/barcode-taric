"""Άντληση στοιχείων εταιρείας από ΑΦΜ μέσω GEMI Open Data (Business Portal).

Πηγή: https://opendata-api.businessportal.gr (Γενικό Εμπορικό Μητρώο). Χρειάζεται
`BUSINESS_PORTAL_KEY` (header `api_key`). Ο χρήστης βάζει το κλειδί στις Ρυθμίσεις.
Επιστρέφει επωνυμία, διεύθυνση, πόλη, ΤΚ, νομική μορφή, ΓΕΜΗ κ.λπ. για auto-fill πελάτη.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from ..config import SETTINGS
from .http_util import debug, http_json

SEARCH_URL = "https://opendata-api.businessportal.gr/api/opendata/v1/companies"


def _first(source: dict, keys: list[str]) -> str:
    for k in keys:
        v = source.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _format_address(c: dict) -> str:
    addr = c.get("address") if isinstance(c.get("address"), dict) else {}
    raw = _first(c, ["address", "fullAddress", "companyAddress", "headquarterAddress"])
    if raw and not isinstance(c.get("address"), dict):
        return raw
    street = _first({**c, **addr}, ["street", "addressStreet", "streetName", "coStreet"])
    num = _first({**c, **addr}, ["streetNumber", "addressNumber", "streetNo", "coStreetNumber"])
    city = _first({**c, **addr}, ["city", "coCity", "addressCity"])
    zipc = _first({**c, **addr}, ["zipCode", "postalCode", "zip", "coZipCode"])
    return " ".join(p for p in (street, num, city, zipc) if p).strip()


def api_key() -> str:
    return str(SETTINGS.get("business_portal_key") or os.getenv("BUSINESS_PORTAL_KEY") or "").strip()


def lookup_by_afm(afm: str) -> dict[str, Any]:
    """Επιστρέφει {success, company{name,vat,address,city,zip,activity,legal_form,ar_gemi}, error}."""
    result: dict[str, Any] = {"success": False, "company": {}, "error": None}
    afm = "".join(ch for ch in str(afm) if ch.isdigit())
    if len(afm) < 9:
        result["error"] = "Μη έγκυρο ΑΦΜ (χρειάζονται 9 ψηφία)."
        return result
    key = api_key()
    if not key:
        result["error"] = "Δεν έχει οριστεί Business Portal API key (Ρυθμίσεις)."
        return result

    params = {"afm": afm.zfill(9), "resultsSortBy": "+arGemi", "resultsOffset": 0, "resultsSize": 5}
    import urllib.parse
    url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"
    try:
        data = http_json(url, timeout=30, headers={"accept": "application/json", "api_key": key})
    except Exception as exc:  # noqa: BLE001
        debug(f"business lookup failed: {exc}")
        result["error"] = f"Σφάλμα σύνδεσης: {str(exc)[:80]}"
        return result

    results = data.get("searchResults") if isinstance(data, dict) else None
    company = (results or [None])[0] if results else (data if isinstance(data, dict) else None)
    if not company:
        result["error"] = "Δεν βρέθηκε εταιρεία για αυτό το ΑΦΜ."
        return result

    result["success"] = True
    result["company"] = {
        "name": _first(company, ["coNameEl", "companyName", "name", "coName", "title"]),
        "vat": _first(company, ["afm", "vatNumber"]) or afm,
        "address": _format_address(company),
        "city": _first(company, ["city", "coCity", "addressCity"]),
        "zip": _first(company, ["zipCode", "postalCode", "coZipCode"]),
        "activity": _first(company, ["kad", "kadDescription", "activity", "coActivity",
                                     "mainActivity", "activityDescription"]),
        "legal_form": _first(company, ["legalForm", "legalFormLabel", "legalType",
                                       "legalTypeLabel", "companyLegalForm"]),
        "ar_gemi": _first(company, ["arGemi", "ArGemi"]),
    }
    return result
