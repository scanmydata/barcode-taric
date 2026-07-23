"""Αυτόματη λήψη & ενημέρωση TARIC ονοματολογίας από την επίσημη πύλη ΕΕ CIRCABC.

Πηγή: CIRCABC group «Taric and Quota Data & Information» → Library → «TARIC data»
(node 64db9d0f-…). Η δομή είναι: TARIC data → <έτος> → <μήνας> → αρχεία, όπου το
«Nomenclature EL.xlsx» / «Nomenclature EN.xlsx» περιέχουν την πλήρη ονοματολογία.

Public REST (guest): /service/circabc/... . Download αρχείων: /d/d/workspace/SpacesStore/{id}/{name}.
Δεν χρειάζεται login/κλειδί — τα δεδομένα είναι δημόσια.
"""

from __future__ import annotations

import json
import re
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from ..engine.http_util import BROWSER_UA, debug
from .. import repo
from . import importer

BASE = "https://circabc.europa.eu/service/circabc"
DOWNLOAD = "https://circabc.europa.eu/d/d/workspace/SpacesStore/{id}/{name}"
TARIC_DATA_NODE = "64db9d0f-e7c9-4084-afe9-f47e70e53c10"


def _get_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def _subspaces(node: str) -> list[dict]:
    url = f"{BASE}/spaces/{node}/subspaces?language=en&guest=true&sort=title&order=ASC"
    data = _get_json(url)
    return data if isinstance(data, list) else (data.get("data") or [])


def _files(node: str) -> list[dict]:
    url = (f"{BASE}/spaces/{node}/children?language=en&guest=true&limit=300&page=1"
           "&order=name_ASC&folderOnly=false&fileOnly=true&skipExpiredItems=true")
    data = _get_json(url)
    return data if isinstance(data, list) else (data.get("data") or [])


def _name(item: dict) -> str:
    return str(item.get("name") or item.get("title") or "").strip()


def _numeric_first(items: list[dict]) -> Optional[dict]:
    """Επιστρέφει το item με το μεγαλύτερο αριθμητικό prefix (π.χ. έτος/μήνας)."""
    best, best_val = None, -1
    for it in items:
        m = re.match(r"\s*(\d+)", _name(it))
        if m and int(m.group(1)) > best_val:
            best_val, best = int(m.group(1)), it
    return best or (items[-1] if items else None)


def find_latest_nomenclature(progress: Optional[Callable[[str], None]] = None) -> Optional[dict]:
    """Πλοηγείται TARIC data → τελευταίο έτος → τελευταίο μήνα → βρίσκει EL/EN αρχεία."""
    if progress:
        progress("Σύνδεση με CIRCABC (ΕΕ)…")
    years = _subspaces(TARIC_DATA_NODE)
    year = _numeric_first(years)
    if not year:
        return None
    if progress:
        progress(f"Έτος: {_name(year)}")
    months = _subspaces(year["id"])
    month = _numeric_first(months)
    if not month:
        return None
    if progress:
        progress(f"Μήνας: {_name(month)} — ανάγνωση αρχείων…")
    files = _files(month["id"])

    el = _find_file(files, "nomenclature el")
    en = _find_file(files, "nomenclature en")
    if not el and not en:
        return None
    version = f"CIRCABC {_name(year)}/{_name(month).split()[0]}"
    return {"version": version, "year": _name(year), "month": _name(month),
            "el": el, "en": en}


def _find_file(files: list[dict], needle: str) -> Optional[dict]:
    needle = needle.lower()
    for f in files:
        if _name(f).lower().startswith(needle) or needle in _name(f).lower():
            return {"id": f.get("id"), "name": _name(f)}
    return None


def download_file(node_id: str, name: str, dest: Path,
                  progress: Optional[Callable[[str], None]] = None) -> Path:
    url = DOWNLOAD.format(id=node_id, name=urllib.parse.quote(name))
    if progress:
        progress(f"Λήψη «{name}»…")
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        dest.write_bytes(r.read())
    return dest


def auto_import(progress: Optional[Callable[[str], None]] = None) -> int:
    """Κατεβάζει EL+EN nomenclature από το πιο πρόσφατο CIRCABC snapshot & κάνει import."""
    info = find_latest_nomenclature(progress)
    if not info:
        raise RuntimeError("Δεν βρέθηκαν αρχεία ονοματολογίας στο CIRCABC.")

    tmpdir = Path(tempfile.mkdtemp(prefix="circabc_"))
    try:
        el_path = en_path = None
        if info.get("el"):
            el_path = download_file(info["el"]["id"], info["el"]["name"],
                                    tmpdir / "nomen_el.xlsx", progress)
        if info.get("en"):
            en_path = download_file(info["en"]["id"], info["en"]["name"],
                                    tmpdir / "nomen_en.xlsx", progress)
        if progress:
            progress("Ανάλυση ονοματολογίας (ιεραρχία + περιγραφές)…")
        rows = importer.parse_nomenclature(el_path or en_path, en_path if el_path else None,
                                           version=info["version"])
        if not rows:
            raise RuntimeError("Η ανάλυση της ονοματολογίας δεν επέστρεψε εγγραφές.")
        if progress:
            progress(f"Εισαγωγή {len(rows)} κωδικών TARIC…")
        return repo.bulk_insert_taric(rows, version=info["version"],
                                      source_url="https://circabc.europa.eu (TARIC data)")
    finally:
        for p in tmpdir.glob("*"):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            tmpdir.rmdir()
        except OSError:
            pass


def latest_available_version(progress: Optional[Callable[[str], None]] = None) -> Optional[str]:
    """Μόνο η ετικέτα της τελευταίας διαθέσιμης έκδοσης (για check-for-updates)."""
    info = find_latest_nomenclature(progress)
    return info["version"] if info else None
