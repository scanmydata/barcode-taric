"""Κατέβασμα PDF από Epsilon Digital DocViewer — functional test.

ΕΥΡΗΜΑ (σημαντικό):
  Η σελίδα DocViewer (το HTML/Blazor UI) είναι πίσω από **Cloudflare Turnstile
  CAPTCHA** — το κουμπί «Αποθήκευση ως PDF» δεν κάνει καν render μέχρι να περάσει
  το challenge. Δεν παρακάμπτουμε CAPTCHA/bot-detection.

  ΟΜΩΣ δεν χρειάζεται: το ίδιο το endpoint που δείχνει το κουμπί,
  δηλαδή  /filedocument/getfile?fileType=2&documentId=<id>
  είναι απευθείας προσβάσιμο με απλό HTTP GET (χωρίς cookies/CAPTCHA) και
  επιστρέφει το PDF. Άρα κατεβάζουμε το αρχείο κατευθείαν από το endpoint —
  ό,τι ακριβώς κάνει το κουμπί, χωρίς browser/automation.

fileType τιμές που παρατηρήθηκαν στο endpoint:
  0 = JSON metadata, 1 = text, 2 = PDF, 3/4 = UBL invoice XML.
  Αν το fileType=2 γυρίσει 404 -> το document ΔΕΝ έχει server-side PDF
  (ο viewer το παράγει client-side), οπότε δεν υπάρχει αρχείο να κατέβει.

Χρήση:
    PYTHONUTF8=1 .venv\\Scripts\\python scripts\\epsilon_pdf_download_test.py
    PYTHONUTF8=1 .venv\\Scripts\\python scripts\\epsilon_pdf_download_test.py <docviewer_url> ...
"""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

DOWNLOAD_DIR = Path(__file__).resolve().parent.parent / "_pdf_downloads"

# Default DocViewer links προς δοκιμή.
DEFAULT_LINKS = [
    "https://epsilondigital6.epsilonnet.gr/DocViewer/1d836c50-f190-4cb8-4966-08de7cae9d38",
    "https://epsilondigital14.epsilonnet.gr/DocViewer/14e0101f-23ad-47f2-35c2-08ddef1e840a",
]

_DOCVIEWER_RE = re.compile(
    r"^(https?://[^/]+)/DocViewer/([0-9a-fA-F-]{36})", re.IGNORECASE
)


def _pdf_url_from_docviewer(url: str) -> tuple[str, str] | None:
    """DocViewer URL -> (origin, documentId). None αν δεν ταιριάζει."""
    m = _DOCVIEWER_RE.match(url.strip())
    if not m:
        return None
    return m.group(1), m.group(2).lower()


def download_pdf(docviewer_url: str, out_dir: Path) -> bool:
    parsed = _pdf_url_from_docviewer(docviewer_url)
    if parsed is None:
        print(f"[skip] μη έγκυρο DocViewer URL: {docviewer_url}")
        return False
    origin, doc_id = parsed
    pdf_url = f"{origin}/filedocument/getfile?fileType=2&documentId={doc_id}"
    print(f"\n=== {docviewer_url}")
    print(f"    PDF endpoint: {pdf_url}")
    req = urllib.request.Request(pdf_url, headers={"User-Agent": UA})
    try:
        resp = urllib.request.urlopen(req, timeout=45)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print("    [404] δεν υπάρχει server-side PDF για αυτό το document")
            print("          (ο viewer το παράγει client-side — δεν υπάρχει αρχείο να κατέβει)")
        else:
            print(f"    [fail] HTTP {exc.code}")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"    [fail] {type(exc).__name__}: {exc}")
        return False

    ctype = resp.headers.get("Content-Type", "")
    data = resp.read()
    if not data.startswith(b"%PDF-"):
        print(f"    [fail] η απάντηση δεν είναι PDF (Content-Type={ctype}, head={data[:16]!r})")
        return False

    out_dir.mkdir(parents=True, exist_ok=True)
    host = origin.split("//", 1)[-1].split(".", 1)[0]
    dest = out_dir / f"{host}_{doc_id[:8]}.pdf"
    dest.write_bytes(data)
    print(f"    [ok] {ctype}, {len(data):,} bytes -> {dest}")
    return True


def main() -> int:
    links = [a for a in sys.argv[1:] if not a.startswith("--")] or DEFAULT_LINKS
    print(f"Download dir: {DOWNLOAD_DIR}")
    results = [(u, download_pdf(u, DOWNLOAD_DIR)) for u in links]
    print("\n===== ΣΥΝΟΨΗ =====")
    for url, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {url}")
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
