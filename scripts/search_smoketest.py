"""Λειτουργικό τεστ web search (headed/headless browser + όλα τα tiers).

Τρέξε:
    .venv\\Scripts\\python scripts\\search_smoketest.py                 # headless
    .venv\\Scripts\\python scripts\\search_smoketest.py --headed        # ορατό παράθυρο Chrome
    .venv\\Scripts\\python scripts\\search_smoketest.py "δικό μου query"

Δείχνει: (1) ποιο tier απαντά ανά query, (2) όλα τα tiers ξεχωριστά (debugger),
(3) απευθείας το headless browser (undetected-chromedriver -> plain selenium fallback).
Δεν είναι μέρος του pytest suite (χρειάζεται δίκτυο/Chrome) — είναι χειροκίνητο smoke test.
"""

from __future__ import annotations

import sys
import time

# UTF-8 stdout σε Windows (cp1252 σκάει στα ελληνικά).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pass

from barcodetaric.config import SETTINGS
from barcodetaric.engine import web_search as ws


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    headed = "--headed" in sys.argv
    queries = args or [
        "Στάμου γάλα αγελάδος παστεριωμένο πλήρες 1lt",
        "Merenda πραλίνα φουντουκιού 360g",
    ]

    SETTINGS.set("headless_headed", headed)
    print(f"== ρυθμίσεις: headed={headed}, engine={SETTINGS.get('headless_engine')}, "
          f"undetected={SETTINGS.get('headless_undetected')} ==\n")

    print("== 1) search_web (ολόκληρη αλυσίδα tiers) ==")
    for q in queries:
        t = time.time()
        res = ws.search_web(q, limit=5)
        print(f"\n  QUERY: {q}\n  -> {len(res)} results σε {time.time()-t:.1f}s")
        for r in res[:4]:
            print(f"     • {r['title'][:70]}")

    print("\n== 2) test_tiers (κάθε tier ξεχωριστά) ==")
    for name, ok, msg in ws.test_tiers(queries[0]):
        print(f"  [{'✓' if ok else '×'}] {name:14} {msg}")

    print("\n== 3) headless browser απευθείας ==")
    drv = ws._headless_driver()
    print(f"  driver: {type(drv).__name__ if drv else 'None (selenium/Chrome λείπει)'}")
    if drv is not None:
        t = time.time()
        res = ws._via_headless(queries[0], 5)
        print(f"  -> {len(res)} results σε {time.time()-t:.1f}s")
        for r in res[:4]:
            print(f"     • {r['title'][:70]}")
        try:
            drv.quit()
        except Exception:  # noqa: BLE001 - noisy teardown (uc/WinError 6)
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
