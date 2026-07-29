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

from . import ai, embeddings, translation_api
from .ml_classifier import get_model
from ..config import SETTINGS
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


# Θόρυβος που ΒΛΑΠΤΕΙ την κατάταξη: ποσότητες/μεγέθη/ποσοστά/συσκευασία + brand.
# Π.χ. «ΝΟΥΝΟΥ γιαούρτι 1,5% 2x175g» -> «γιαούρτι»: το «1,5%», «2x175g», «ΝΟΥΝΟΥ»
# παρασέρνουν και το FTS και τα embeddings (π.χ. σε πρωτεϊνικά supplements αντί γιαουρτιού).
_QTY_PATTERNS = [
    re.compile(r"\b\d+[.,]?\d*\s*(?:x|×)\s*\d+[.,]?\d*\s*(?:g|gr|kg|ml|cl|l|lt|lit|τεμ|pcs?)\b", re.I),
    re.compile(r"\b\d+[.,]?\d*\s*(?:g|gr|kg|ml|cl|l|lt|lit|oz|lb|τεμ|pcs?)\b", re.I),
    re.compile(r"\b\d+[.,]?\d*\s*%|\b\d+[.,]?\d*\s*(?:vol|λιπαρ\w*|fat)\b", re.I),
    re.compile(r"\b\d+\s*(?:x|×)\s*\d+\b", re.I),
    re.compile(r"\b(?:pack|συσκευασ\w*|τεμαχ\w*)\b", re.I),
]
_MARKETING_TOKENS = {
    "new", "νεο", "νέο", "offer", "προσφορα", "value", "family", "οικογενειακη",
    "premium", "classic", "original", "χωρις", "χωρίς", "free",  # «χωρίς λακτόζη»: κρατάμε «λακτόζη»? όχι, δεν αλλάζει κατάταξη
    "lactose", "λακτοζη", "λακτόζη",
}


def clean_for_classification(text: str, *, brand: str = "") -> str:
    """Αφαιρεί θόρυβο (ποσότητα/μέγεθος/ποσοστά/μάρκα/marketing) ώστε να μείνει το
    ΕΙΔΟΣ του προϊόντος — αυτό που καθορίζει την τελωνειακή κατάταξη."""
    out = text or ""
    for pat in _QTY_PATTERNS:
        out = pat.sub(" ", out)
    tokens = out.split()
    brand_toks = {t for t in _norm(brand).split() if len(t) > 1} if brand else set()
    kept = []
    for tok in tokens:
        n = _norm(tok)
        if not n:
            continue
        if n in brand_toks or n in _MARKETING_TOKENS:
            continue
        kept.append(tok)
    cleaned = re.sub(r"\s+", " ", " ".join(kept)).strip()
    return cleaned or text  # ποτέ κενό (αν όλα ήταν «θόρυβος», κράτα το αρχικό)


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

    # PRIMARY retrieval σε σειρά BM25 (η θέση δίνει relevance bonus πιο κάτω).
    primary = repo.search_taric(query, limit=120)
    pos = {r.code: i for i, r in enumerate(primary)}
    pool: dict[str, object] = {r.code: r for r in primary}
    # UNION retrieval: ψάξε ΚΑΙ κάθε σημαντικό όρο ξεχωριστά — εγγυάται ότι το heading του
    # ΒΑΣΙΚΟΥ ουσιαστικού (milk/γάλα, butter/βούτυρο) μπαίνει στο pool, ακόμη κι όταν το
    # bm25 του σύνθετου query «θάβει» τη γενική επικεφαλίδα κάτω από σπάνιους προσδιορισμούς.
    for tok in list(qtokens)[:12]:
        for r in repo.search_taric(tok, limit=40):
            pool.setdefault(r.code, r)

    # Score = IDF-coverage (_score) + BM25 relevance bonus. Το bonus κρατά τη σωστή σειρά
    # retrieval ώστε μια ΣΠΑΝΙΑ λέξη-επίθετο (π.χ. «unsalted») να μη σπρώξει άσχετο κεφάλαιο
    # (αποξηραμένος μπακαλιάρος) πάνω από τη λέξη-πυρήνα («butter»). union-only rows -> bonus ~0.
    n = max(len(primary), 1)
    scored = []
    for code, r in pool.items():
        s = _score(qtokens, r)
        if s <= 0:
            continue
        rel_bonus = 0.30 * (1.0 - pos.get(code, n) / n)
        scored.append((s + rel_bonus, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    scored = [(s, r) for s, r in scored if s > 0]
    # DIVERSITY: μη γεμίζει όλο το top με sub-codes ΜΙΑΣ επικεφαλίδας (π.χ. δεκάδες 1901…),
    # αφήνοντας απ' έξω τη σωστή γειτονική κλάση (0401/0402 Γάλα). Κράτα ≤2 ανά hs4 σε πρώτο
    # πέρασμα ώστε να μπουν ΔΙΑΦΟΡΕΤΙΚΕΣ κλάσεις -> το AI/ML βλέπει και το σωστό κεφάλαιο.
    per_hs4: dict[str, int] = {}
    diverse: list = []
    overflow: list = []
    for s, r in scored:
        hs4 = (getattr(r, "hs4", "") or r.code[:4])
        if per_hs4.get(hs4, 0) < 2:
            per_hs4[hs4] = per_hs4.get(hs4, 0) + 1
            diverse.append((s, r))
        else:
            overflow.append((s, r))
        if len(diverse) >= top:
            break
    # αν δεν γέμισε (λίγες διακριτές κλάσεις), συμπλήρωσε από το overflow με τη σειρά score.
    if len(diverse) < top:
        diverse.extend(overflow[: top - len(diverse)])
    return diverse[:top]


_FOOD_SOURCES = ("openfoodfacts", "off")


def _is_food_source(source: str) -> bool:
    return any(s in (source or "").lower() for s in _FOOD_SOURCES)


def _is_food_chapter(code: str) -> bool:
    """HS κεφάλαια 01-24 = τρόφιμα/ποτά/ζωικά/φυτικά προϊόντα."""
    return len(code) >= 2 and code[:2].isdigit() and 1 <= int(code[:2]) <= 24


def match(description_el: str, description_en: str = "", *, barcode: str = "",
          brand: str = "", quantity: str = "", categories: str = "",
          analysis: str = "", source: str = "", use_ai: bool = True) -> MatchResult:
    description_el = (description_el or "").strip()
    description_en = (description_en or "").strip()

    # English-first: η επίσημη ΕΕ ονοματολογία (CN/HS) είναι τυποποιημένη στα Αγγλικά,
    # οπότε η κατάταξη είναι ακριβέστερη με αγγλικό query. Αν λείπει το EN αλλά υπάρχει
    # EL, το μεταφράζουμε μέσω του δωρεάν tier (χωρίς LLM) πριν το scoring/AI ranking.
    if SETTINGS.get("classify_in_english", True) and description_el and not description_en:
        translated = translation_api.to_english(description_el)
        if translated and translated.strip().lower() != description_el.strip().lower():
            description_en = translated.strip()

    combined = f"{description_en} {description_el}".strip()  # EN πρώτο (βασική γλώσσα)
    # Καθαρισμένο query για την κατάταξη (χωρίς brand/ποσότητα/marketing θόρυβο).
    clean_en = clean_for_classification(description_en, brand=brand)
    clean_el = clean_for_classification(description_el, brand=brand)
    clean_combined = f"{clean_en} {clean_el}".strip() or combined

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
        pred = model.predict(description_el, description_en, barcode, brand, quantity,
                             categories, analysis)
        if pred and pred.stage == "taric" and pred.code:
            desc = _lookup_taric_desc(pred.code)
            return MatchResult(taric_code=pred.code, hs4=pred.hs4, taric_description=desc,
                               confidence=pred.confidence, taric_source="ml",
                               ai_rationale="Πρόβλεψη τοπικού μοντέλου ML.")

    # (γ) FTS (λέξεις, union+brand-removal+BM25) + ΕΝΝΟΙΟΛΟΓΙΚΑ embeddings (νόημα).
    # top=8: περισσότεροι υποψήφιοι για το AI rank ώστε να υπάρχει ο σωστός ακόμη κι όταν
    # το keyword scoring τον βάζει 3ο-8ο. Χρησιμοποιούμε το καθαρισμένο query (χωρίς θόρυβο).
    cands = fts_candidates(clean_el, clean_en, brand=brand, top=8)
    # Chapter prior: αν η πηγή είναι τρόφιμο (OpenFoodFacts), κράτα κεφάλαια τροφίμων/ποτών
    # (HS 01-24) — αλλιώς «X water» πέφτει σε 3303 (άρωμα) αντί 2201 (μεταλλικό νερό).
    if _is_food_source(source) and cands:
        food = [(s, r) for s, r in cands if _is_food_chapter(r.code)]
        if food:
            cands = food
    sem = embeddings.semantic_candidates(clean_combined, top=6) if clean_combined else []
    fts_top = cands[0][0] if cands else 0.0
    sem_top = sem[0][0] if sem else 0.0
    # Guard: το semantic είναι θορυβώδες σε ονόματα προϊόντων· «οδηγεί» μόνο αν ΣΥΜΦΩΝΕΙ με
    # το FTS στο HS4 (ή αν το FTS είναι κενό). Αλλιώς εμπιστευόμαστε το λεξιλογικά ακριβές FTS.
    fts_hs4 = {(getattr(r, "hs4", "") or "")[:4] for _s, r in cands if getattr(r, "hs4", "")}
    sem_agrees = bool(sem and (not fts_hs4 or (getattr(sem[0][1], "hs4", "") or "")[:4] in fts_hs4))
    cand_dicts = _merge_candidates(cands, sem)

    # (δ) AI rank + rationalization (μόνο αν διαθέσιμο & υπάρχουν υποψήφιοι)
    if use_ai and cand_dicts and ai.ai_available():
        ranked = ai.rank_taric(clean_combined, cand_dicts)
        if ranked:
            chosen = next((c for c in cand_dicts if c["code"] == ranked["code"]), cand_dicts[0])
            return MatchResult(taric_code=ranked["code"], hs4=chosen.get("hs4") or ranked["code"][:4],
                               taric_description=chosen.get("description_el") or chosen.get("description_en", ""),
                               confidence=ranked.get("confidence", 0.6),
                               ai_rationale=ranked.get("rationale", ""), taric_source="ai",
                               candidates=cand_dicts)

    # fallback χωρίς AI: το semantic «οδηγεί» ΜΟΝΟ αν συμφωνεί με το FTS στο HS4
    # (ή αν το FTS είναι κενό) — αλλιώς εμπιστευόμαστε το λεξιλογικά ακριβές FTS.
    if sem and sem_agrees and sem_top >= 0.45 and sem_top >= fts_top:
        top_row = sem[0][1]
        return MatchResult(taric_code=top_row.code, hs4=top_row.hs4 or top_row.code[:4],
                           taric_description=top_row.description_el or top_row.description_en,
                           confidence=round(min(0.6, sem_top), 2), taric_source="semantic",
                           ai_rationale="Εννοιολογική αντιστοίχιση (embeddings) στην ΕΕ ονοματολογία.",
                           candidates=cand_dicts)
    if cands:
        top_score, top_row = cands[0]
        return MatchResult(taric_code=top_row.code, hs4=top_row.hs4 or top_row.code[:4],
                           taric_description=top_row.description_el or top_row.description_en,
                           confidence=min(0.5, round(top_score, 2)), taric_source="fts",
                           ai_rationale="Καλύτερη αντιστοίχιση full-text στην ΕΕ ονοματολογία.",
                           candidates=cand_dicts)

    return MatchResult(taric_source="none")


def _merge_candidates(fts: list, sem: list) -> list[dict]:
    """Ένωση FTS + semantic υποψηφίων (dedup ανά code, FTS σειρά πρώτα)."""
    out: list[dict] = []
    seen: set[str] = set()
    for _s, r in list(fts) + list(sem):
        if r.code in seen:
            continue
        seen.add(r.code)
        out.append({"code": r.code,
                    "description_el": getattr(r, "description_path_el", "") or r.description_el,
                    "description_en": getattr(r, "description_path_en", "") or r.description_en,
                    "hs4": r.hs4})
    return out


def _lookup_taric_desc(code: str) -> str:
    rows = repo.search_taric(code, limit=1)
    if rows:
        return rows[0].description_el or rows[0].description_en
    return ""
