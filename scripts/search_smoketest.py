"""Λειτουργικό τεστ web search (headed/headless browser) + AI rationalization.

Τρέξε:
    .venv\\Scripts\\python scripts\\search_smoketest.py                    # headless, default engine
    .venv\\Scripts\\python scripts\\search_smoketest.py --headed           # ορατό παράθυρο Chrome
    .venv\\Scripts\\python scripts\\search_smoketest.py --engine brave     # search μέσω search.brave.com
    .venv\\Scripts\\python scripts\\search_smoketest.py "δικό μου query"

Δείχνει: (1) search_web αλυσίδα, (2) κάθε tier ξεχωριστά, (3) headless browser απευθείας,
(4) ΤΟ ΠΛΗΡΕΣ ΡΟΗ: search -> format context -> AI (confirm_product) rationalization
    -> δομημένη ΑΝΑΛΥΣΗ που φεύγει στην κατάταξη TARIC. Λειτουργεί με local LLM (custom
    endpoint / ollama qwen) ή OpenRouter — ό,τι είναι ρυθμισμένο.
Δεν είναι μέρος του pytest suite (χρειάζεται δίκτυο/Chrome) — χειροκίνητο smoke test.
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
from barcodetaric.engine import ai, web_search as ws


def _arg_value(flag: str, default: str) -> str:
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def main() -> int:
    flags = {"--headed", "--engine"}
    engine = _arg_value("--engine", str(SETTINGS.get("headless_engine") or "bing"))
    skip = {engine} if "--engine" in sys.argv else set()
    args = [a for a in sys.argv[1:] if not a.startswith("--") and a not in skip]
    headed = "--headed" in sys.argv
    queries = args or [
        "Στάμου γάλα αγελάδος παστεριωμένο πλήρες 1lt",
        "Merenda πραλίνα φουντουκιού 360g",
    ]

    SETTINGS.set("headless_headed", headed)
    SETTINGS.set("headless_engine", engine)
    print(f"== ρυθμίσεις: headed={headed}, engine={engine}, "
          f"undetected={SETTINGS.get('headless_undetected')}, "
          f"ai_order={SETTINGS.get('ai_provider_order')} ==\n")

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

    print(f"\n== 3) headless browser απευθείας (engine={engine}) ==")
    drv = ws._headless_driver()
    print(f"  driver: {type(drv).__name__ if drv else 'None (selenium/Chrome λείπει)'}")
    if drv is not None:
        for q in queries:
            t = time.time()
            res = ws._via_headless(q, 5)
            print(f"  {q[:34]!r} -> {len(res)} results σε {time.time()-t:.1f}s")
            for r in res[:3]:
                print(f"     • {r['title'][:60]} || {(r.get('snippet') or '')[:40]}")
        try:
            drv.quit()
        except Exception:  # noqa: BLE001 - noisy teardown (uc/WinError 6)
            pass

    print("\n== 4) ΠΛΗΡΗΣ ΡΟΗ: search -> format -> AI rationalization ==")
    if not ai.ai_available():
        print("  (AI μη διαθέσιμο — ρύθμισε OpenRouter key ή custom endpoint/ollama)")
        return 0
    for q in queries:
        ctx = ws.gather_context(name=q, limit=5)
        confirmed = ai.confirm_product(candidate_name=q, web_context=ctx.get("text", ""))
        print(f"\n  QUERY: {q}")
        if not confirmed:
            print("     -> AI δεν επέστρεψε έγκυρο αποτέλεσμα")
            continue
        print(f"     name_en : {confirmed.get('name_en')}")
        print(f"     hint    : {confirmed.get('customs_hint')}")
        print(f"     ANALYSIS: {confirmed.get('analysis')}")
        print(f"     product={confirmed.get('is_product')} conf={confirmed.get('confidence')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
