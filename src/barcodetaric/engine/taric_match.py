"""Ενορχήστρωση αντιστοίχισης TARIC σε επίπεδα αυξανόμενου κόστους.

  (α) catalog  — γνωστό barcode που έχει ήδη επιβεβαιωμένο/αποθηκευμένο TARIC
  (β) ML       — τοπικό μοντέλο· αν confidence >= threshold, χωρίς AI
  (γ) FTS      — full-text search στην επίσημη ΕΕ ονοματολογία + token scoring
  (δ) AI       — rank στους top υποψηφίους + rationalization (μόνο όταν χρειάζεται)

Επιστρέφει `MatchResult` έτοιμο για αποθήκευση σε client_items/catalog.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

from . import ai
from .ml_classifier import get_model
from .. import repo


@dataclass
class MatchResult:
    taric_code: str = ""
    hs4: str = ""
    taric_description: str = ""
    confidence: float = 0.0
    ai_rationale: str = ""
    taric_source: str = ""   # catalog | ml | fts | ai | none
    candidates: list = field(default_factory=list)


_STOPWORDS = {
    "and", "or", "for", "with", "the", "a", "an", "of", "to", "in", "on", "other",
    "και", "με", "σε", "για", "του", "της", "των", "στο", "στη", "στον", "αλλα", "λοιπα",
    # Μονάδες/ποσότητες & marketing-προσδιορισμοί: ΔΕΝ είναι κριτήρια δασμολογικής κλάσης
    # και «τραβάνε» σε άσχετες γραμμές (π.χ. «ελαφρύ»->ελαφρό σκυρόδεμα, «φρέσκο»->νωπή ξυλεία).
    "lt", "ltr", "l", "ml", "cl", "kg", "gr", "gram", "grammar", "γρ", "kgr", "τεμ", "τεμαχια",
    "pack", "συσκευασια", "τεμαχιο", "φρεσκο", "φρεσκα", "fresh", "ελαφρυ", "ελαφρια", "light",
    "premium", "νεο", "new", "classic", "original",
}


def _norm(text: str) -> str:
    """Πεζά + αφαίρεση τόνων, ΚΡΑΤΩΝΤΑΣ Ελληνικά και Λατινικά."""
    lowered = text.lower()
    stripped = "".join(c for c in unicodedata.normalize("NFKD", lowered)
                       if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9α-ω\s]", " ", stripped)).strip()


def _tokens(text: str) -> set[str]:
    from .http_util import stem_token
    return {stem_token(t) for t in _norm(text).split() if t not in _STOPWORDS and len(t) > 1}


# ------------------------------------------------------------ IDF weighting ----
# Κοινές λέξεις (νερό/water/other/άλλα) ταιριάζουν παντού και «μολύνουν» το score.
# Το IDF (inverse document frequency) τους δίνει μικρό βάρος και ενισχύει τις σπάνιες
# (coffee/chocolate/mineral). Υπολογίζεται μία φορά ανά dataset (cache με row-count).
_IDF: dict[str, float] = {}
_IDF_N: int = 0
_IDF_ROWCOUNT: int = -1


def _idf() -> dict[str, float]:
    global _IDF, _IDF_N, _IDF_ROWCOUNT
    rc = repo.taric_row_count()
    if rc == _IDF_ROWCOUNT and _IDF:
        return _IDF
    df: dict[str, int] = {}
    texts = repo.iter_taric_texts()
    for text in texts:
        for t in _tokens(text):
            df[t] = df.get(t, 0) + 1
    n = max(1, len(texts))
    _IDF = {t: math.log(1 + n / (1 + c)) for t, c in df.items()}
    _IDF_N = n
    _IDF_ROWCOUNT = rc
    return _IDF


# Πλαφόν IDF: χωρίς αυτό, σπάνιοι ΠΡΟΣΔΙΟΡΙΣΜΟΙ (π.χ. «αγελάδος», «παστεριωμένο», «ελαφρύ»)
# παίρνουν τεράστιο βάρος και «πνίγουν» το βασικό ουσιαστικό (γάλα) — που είναι κοινό άρα χαμηλό
# IDF. Για ταξινόμηση προϊόντων ο τύπος του προϊόντος μετράει, όχι οι επιθετικοί προσδιορισμοί.
_IDF_CAP = 5.0


def _w(token: str) -> float:
    """Βάρος token: IDF (με πλαφόν) αν υπάρχει dataset, αλλιώς 1.0 (ουδέτερο)."""
    idf = _idf()
    raw = idf.get(token, math.log(1 + _IDF_N) if _IDF_N else 1.0)
    return min(raw, _IDF_CAP)


def _token_matches(q: str, row_tokens: set[str]) -> bool:
    if q in row_tokens:
        return True
    if len(q) >= 4:
        for r in row_tokens:
            # Prefix match ΜΟΝΟ όταν τα μήκη είναι κοντά (diff <= 2). Αλλιώς σκέτο brand
            # όπως «δελτα»(5) ταίριαζε λάθος «δελταμεθρινη»(12) -> γάλα κατατασσόταν ως pesticide.
            if len(r) >= 4 and abs(len(r) - len(q)) <= 2 and (q.startswith(r) or r.startswith(q)):
                return True
    return False


def _row_text(row) -> str:
    """Προτίμησε τη σύνθετη περιγραφή με το γονικό context (αν υπάρχει)."""
    el = getattr(row, "description_path_el", "") or row.description_el
    en = getattr(row, "description_path_en", "") or row.description_en
    return f"{el} {en}"


def _score(query_tokens: set[str], row) -> float:
    row_tokens = _tokens(_row_text(row))
    if not row_tokens or not query_tokens:
        return 0.0
    matched = [q for q in query_tokens if _token_matches(q, row_tokens)]
    if not matched:
        return 0.0
    # IDF-σταθμισμένη (με πλαφόν) κάλυψη του query.
    matched_w = sum(_w(q) for q in matched)
    query_w = sum(_w(q) for q in query_tokens) or 1.0
    coverage = matched_w / query_w
    # μικρό μπόνους για συντομία της περιγραφής (πιο ειδική)
    brevity = 1.0 / (1 + 0.02 * len(row_tokens))
    return coverage + 0.1 * brevity


def fts_candidates(description_el: str, description_en: str, *, brand: str = "",
                   top: int = 5) -> list:
    query = f"{description_el} {description_en}".strip()
    if not query:
        return []
    # Αφαίρεσε τα brand tokens από το scoring (η μάρκα δεν είναι κριτήριο δασμολογικής κλάσης).
    brand_tokens = _tokens(brand) if brand else set()
    qtokens = _tokens(query) - brand_tokens
    if not qtokens:  # αν έμεινε μόνο η μάρκα, ξαναβάλε τα πάντα
        qtokens = _tokens(query)

    # UNION retrieval: εκτός από το σύνθετο query, ψάξε ΚΑΙ κάθε σημαντικό όρο ξεχωριστά.
    # Το bm25 «θάβει» γενικές επικεφαλίδες (π.χ. 0401 «Γάλα») στο σύνθετο OR-query· η ανά-όρο
    # αναζήτηση εγγυάται ότι οι γραμμές του βασικού ουσιαστικού (milk/γάλα) μπαίνουν στο pool.
    seen: dict[str, object] = {}
    for r in repo.search_taric(query, limit=120):
        seen[r.code] = r
    # Ψάξε ΚΑΘΕ σημαντικό token ξεχωριστά — ΚΑΙ το βασικό ουσιαστικό (milk/γάλα), όχι μόνο
    # τους σπάνιους προσδιορισμούς. Αλλιώς η γενική επικεφαλίδα (0401 Γάλα) δεν μπαίνει καν στο
    # pool, γιατί το «γάλα» είναι κοινό (χαμηλό IDF) και δεν προλαβαίνει το σύνθετο bm25 query.
    for tok in list(qtokens)[:12]:
        for r in repo.search_taric(tok, limit=40):
            seen.setdefault(r.code, r)

    scored = sorted(
        ((_score(qtokens, r), r) for r in seen.values()), key=lambda x: x[0], reverse=True
    )
    return [(s, r) for s, r in scored if s > 0][:top]


def match(description_el: str, description_en: str = "", *, barcode: str = "",
          brand: str = "", quantity: str = "", categories: str = "",
          use_ai: bool = True) -> MatchResult:
    description_el = (description_el or "").strip()
    description_en = (description_en or "").strip()
    combined = f"{description_el} {description_en}".strip()

    # (α) γνωστό barcode στο catalog με έγκυρο TARIC
    if barcode:
        cat = repo.get_catalog_by_barcode(barcode)
        if cat and cat.taric_code:
            return MatchResult(taric_code=cat.taric_code, hs4=cat.hs4 or cat.taric_code[:4],
                               taric_description=cat.taric_description, confidence=cat.confidence or 0.9,
                               ai_rationale=cat.ai_rationale, taric_source="catalog")

    # (β) τοπικό ML
    model = get_model()
    if model.is_ready():
        pred = model.predict(description_el, description_en, barcode, brand, quantity, categories)
        if pred and pred.stage == "taric" and pred.code:
            desc = _lookup_taric_desc(pred.code)
            return MatchResult(taric_code=pred.code, hs4=pred.hs4, taric_description=desc,
                               confidence=pred.confidence, taric_source="ml",
                               ai_rationale="Πρόβλεψη τοπικού μοντέλου ML.")

    # (γ) FTS scoring στην επίσημη ΕΕ ονοματολογία (χωρίς τη μάρκα ως κριτήριο).
    # top=8: δίνουμε περισσότερους υποψηφίους στο AI rank ώστε να υπάρχει ο σωστός ακόμη κι όταν
    # το keyword scoring τον βάζει 3ο-8ο (π.χ. γάλα/καφές κάτω από παρόμοιες γραμμές).
    cands = fts_candidates(description_el, description_en, brand=brand, top=8)
    cand_dicts = [{"code": r.code,
                   "description_el": r.description_path_el or r.description_el,
                   "description_en": r.description_path_en or r.description_en,
                   "hs4": r.hs4} for _, r in cands]

    # (δ) AI rank + rationalization (μόνο αν διαθέσιμο & υπάρχουν υποψήφιοι)
    if use_ai and cand_dicts and ai.ai_available():
        ranked = ai.rank_taric(combined, cand_dicts)
        if ranked:
            chosen = next((c for c in cand_dicts if c["code"] == ranked["code"]), cand_dicts[0])
            return MatchResult(taric_code=ranked["code"], hs4=chosen.get("hs4") or ranked["code"][:4],
                               taric_description=chosen.get("description_el") or chosen.get("description_en", ""),
                               confidence=ranked.get("confidence", 0.6),
                               ai_rationale=ranked.get("rationale", ""), taric_source="ai",
                               candidates=cand_dicts)

    # fallback: κορυφαίος FTS υποψήφιος χωρίς AI
    if cands:
        top_score, top_row = cands[0]
        return MatchResult(taric_code=top_row.code, hs4=top_row.hs4 or top_row.code[:4],
                           taric_description=top_row.description_el or top_row.description_en,
                           confidence=min(0.5, round(top_score, 2)), taric_source="fts",
                           ai_rationale="Καλύτερη αντιστοίχιση full-text στην ΕΕ ονοματολογία.",
                           candidates=cand_dicts)

    return MatchResult(taric_source="none")


def _lookup_taric_desc(code: str) -> str:
    rows = repo.search_taric(code, limit=1)
    if rows:
        return rows[0].description_el or rows[0].description_en
    return ""
