"""Console entry point — batch operations & δοκιμές χωρίς GUI."""

from __future__ import annotations

import argparse
import sys

from . import repo
from .db import init_db
from .engine import resolve
from .engine.ml_classifier import retrain
from .taric import importer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="barcodetaric", description="Barcode/περιγραφή -> TARIC")
    sub = parser.add_subparsers(dest="cmd")

    p_resolve = sub.add_parser("resolve", help="Ανάλυση barcode ή περιγραφής")
    p_resolve.add_argument("query")
    p_resolve.add_argument("--no-ai", action="store_true")

    p_taric = sub.add_parser("import-taric", help="Import ΕΕ ονοματολογίας από αρχείο/URL/seed")
    p_taric.add_argument("source", nargs="?", help="διαδρομή αρχείου ή URL (κενό = seed)")

    sub.add_parser("train", help="Εκπαίδευση τοπικού ML μοντέλου")
    sub.add_parser("gui", help="Εκκίνηση του desktop GUI")

    args = parser.parse_args(argv)
    init_db()

    if args.cmd == "resolve":
        from .engine.barcode_sources import looks_like_barcode
        if looks_like_barcode(args.query):
            res = resolve.resolve_barcode(args.query, use_ai=not args.no_ai)
        else:
            res = resolve.resolve_description(args.query, use_ai=not args.no_ai)
        print(f"Περιγραφή EL: {res.description_el}")
        print(f"Description EN: {res.description_en}")
        print(f"TARIC: {res.taric_code}  HS4: {res.hs4}  ({res.taric_source}, conf={res.confidence:.2f})")
        print(f"Αιτιολόγηση: {res.ai_rationale}")
        return 0

    if args.cmd == "import-taric":
        if not args.source:
            n = importer.import_seed(progress=print)
        elif args.source.startswith(("http://", "https://")):
            n = importer.import_from_url(args.source, progress=print)
        else:
            n = importer.import_from_file(args.source, progress=print)
        print(f"Εισήχθησαν {n} εγγραφές TARIC.")
        return 0

    if args.cmd == "train":
        result = retrain()
        print(result)
        return 0

    if args.cmd == "gui" or args.cmd is None:
        from .gui.app import main as gui_main
        return gui_main()

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
