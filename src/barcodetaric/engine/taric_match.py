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


def _w(token: str) -> float:
    """Βάρος token: IDF αν υπάρχει dataset, αλλιώς 1.0 (ουδέτερο)."""
    idf = _idf()
    return idf.get(token, math.log(1 + _IDF_N) if _IDF_N else 1.0)


def _token_matches(q: str, row_tokens: set[str]) -> bool:
    if q in row_tokens:
        return True
    if len(q) >= 4:
        for r in row_tokens:
            if len(r) >= 4 and (q.startswith(r) or r.startswith(q)):
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
    # IDF-σταθμισμένη κάλυψη του query (σπάνιες λέξεις μετράνε πολύ περισσότερο).
    matched_w = sum(_w(q) for q in matched)
    query_w = sum(_w(q) for q in query_tokens) or 1.0
    coverage = matched_w / query_w
    # μικρό μπόνους για συντομία της περιγραφής (πιο ειδική)
    brevity = 1.0 / (1 + 0.02 * len(row_tokens))
    return coverage + 0.1 * brevity


# --- Chapter prior (χωρίς AI) -------------------------------------------------
# Όταν ξέρουμε τη ΦΥΣΗ της πηγής (π.χ. OpenFoodFacts = τρόφιμο/ποτό), μια
# ομώνυμη λέξη όπως «water» δεν πρέπει να μας στείλει σε «toilet water» (κεφ. 33
# αρώματα). Δίνουμε bonus στα εύλογα κεφάλαια και ποινή στα απίθανα. Αυτό είναι
# η δικλείδα ασφαλείας ΟΤΑΝ το AI δεν είναι διαθέσιμο.
_FOOD_CHAPTERS = {f"{i:02d}" for i in range(1, 25)}         # 01..24 τρόφιμα/ποτά
_NON_FOOD_TRAP_CHAPTERS = {"33", "34"}                       # αρώματα/καλλυντικά, σαπούνια


def _chapter_prior(source: str, categories: str) -> tuple[set[str], set[str]]:
    """(preferred, penalized) HS2 κεφάλαια από την πηγή/κατηγορίες."""
    src = (source or "").lower()
    if "openfoodfacts" in src:
        return _FOOD_CHAPTERS, _NON_FOOD_TRAP_CHAPTERS
    return set(), set()


def _apply_chapter_prior(score: float, row, preferred: set[str], penalized: set[str]) -> float:
    if not preferred and not penalized:
        return score
    chapter = (getattr(row, "hs4", "") or "")[:2]
    if chapter and preferred and chapter in preferred:
        return score * 1.6
    if chapter and penalized and chapter in penalized:
        return score * 0.4
    return score


def fts_candidates(description_el: str, description_en: str, *, top: int = 5,
                   source: str = "", categories: str = "") -> list:
    query = f"{description_el} {description_en}".strip()
    if not query:
        return []
    rows = repo.search_taric(query, limit=60)
    qtokens = _tokens(query)
    preferred, penalized = _chapter_prior(source, categories)
    # BM25 relevance co-signal: το FTS επιστρέφει best-first. Ο IDF _score μόνος του
    # μπορεί να προωθήσει λάθος γραμμή όταν μια ΣΠΑΝΙΑ λέξη-επίθετο (π.χ. «unsalted»)
    # ταιριάζει σε άσχετο κεφάλαιο (αποξηραμένος μπακαλιάρος) πάνω από τη λέξη-πυρήνα
    # («butter»). Κρατώντας τη σειρά retrieval ως ήπιο bonus, δεν ακυρώνεται το BM25.
    n = len(rows) or 1
    scored = []
    for idx, r in enumerate(rows):
        base = _apply_chapter_prior(_score(qtokens, r), r, preferred, penalized)
        if base <= 0:
            continue
        rel_bonus = 0.30 * (1.0 - idx / n)      # 1η θέση +0.30 → φθίνει
        scored.append((base + rel_bonus, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top]


def match(description_el: str, description_en: str = "", *, barcode: str = "",
          brand: str = "", quantity: str = "", categories: str = "",
          source: str = "", use_ai: bool = True) -> MatchResult:
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
        pred = model.predict(description_el, description_en, barcode, brand, quantity, categories)
        if pred and pred.stage == "taric" and pred.code:
            desc = _lookup_taric_desc(pred.code)
            return MatchResult(taric_code=pred.code, hs4=pred.hs4, taric_description=desc,
                               confidence=pred.confidence, taric_source="ml",
                               ai_rationale="Πρόβλεψη τοπικού μοντέλου ML.")

    # (γ) FTS (λέξεις) + ΕΝΝΟΙΟΛΟΓΙΚΑ embeddings (νόημα) στην ΕΕ ονοματολογία.
    # Τα δύο tiers είναι συμπληρωματικά: το FTS πιάνει ακριβείς όρους, τα embeddings
    # πιάνουν συνώνυμα/παραφράσεις. Τα ενώνουμε ώστε το AI να δει πλουσιότερο σύνολο.
    cands = fts_candidates(clean_el, clean_en, top=6, source=source, categories=categories)
    sem = embeddings.semantic_candidates(clean_combined, top=6) if clean_combined else []
    fts_top = cands[0][0] if cands else 0.0
    sem_top = sem[0][0] if sem else 0.0

    # Guard: το semantic είναι θορυβώδες σε ονόματα προϊόντων· επιτρέπεται να «οδηγήσει»
    # μόνο αν ΣΥΜΦΩΝΕΙ με το FTS στο HS4 (ίδιο κεφάλαιο) ή αν το FTS είναι κενό. Αλλιώς
    # εμπιστευόμαστε το FTS (λεξιλογικά ακριβές για όρους όπως «yogurt»).
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
