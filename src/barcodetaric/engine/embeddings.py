"""Τοπικά (offline) πολύγλωσσα embeddings για ΕΝΝΟΙΟΛΟΓΙΚΗ αντιστοίχιση TARIC.

Το FTS τier ταιριάζει *λέξεις*· τα embeddings ταιριάζουν *νόημα* — π.χ. «αναψυκτικό
με ανθρακικό» ↔ «carbonated soft drink» ακόμη κι όταν δεν μοιράζονται λέξεις. Έτσι η
μηχανή αναγνωρίζει τι είναι το προϊόν βάσει περιγραφής/περιεχομένων, όχι μόνο λέξεων.

Σχεδίαση (graceful degradation, όπως το ML tier):
  * Μοντέλο: multilingual sentence-transformer (EL+EN), τοπικό & δωρεάν.
  * Τα embeddings της ΕΕ ονοματολογίας υπολογίζονται ΜΙΑ φορά και cache-άρονται σε
    `taric_embeddings.npz` στο data-dir· ξαναχτίζονται μόνο όταν αλλάξει το row_count.
  * Αν λείπουν sentence-transformers/numpy, το tier απλώς παρακάμπτεται (δεν σκάει).

Το interface (`semantic_candidates`) είναι συμβατό με το FTS tier του `taric_match`,
ώστε τα δύο να ενώνονται πριν το AI ranking.
"""

from __future__ import annotations

from typing import Optional

from ..config import SETTINGS, data_dir
from .. import repo
from .http_util import debug

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Lazy singletons: το μοντέλο φορτώνεται μία φορά ανά process (ακριβό import).
_MODEL = None
_MODEL_FAILED = False

# Cache πίνακα embeddings της ονοματολογίας: (codes, matrix, rowcount).
_MATRIX = None
_CODES: list[str] = []
_ROWCOUNT = -1


def _embeddings_path():
    return data_dir() / "taric_embeddings.npz"


def available() -> bool:
    """True αν οι βιβλιοθήκες embeddings είναι εγκατεστημένες & ενεργές."""
    if SETTINGS.get("semantic_enabled") is False:
        return False
    if _MODEL_FAILED:
        return False
    try:
        import numpy  # noqa: F401
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return True


def _get_model():
    global _MODEL, _MODEL_FAILED
    if _MODEL is not None:
        return _MODEL
    if _MODEL_FAILED:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        name = SETTINGS.get("embedding_model") or DEFAULT_MODEL
        debug(f"loading embedding model: {name}")
        _MODEL = SentenceTransformer(name)
    except Exception as exc:  # noqa: BLE001 - λείπει lib / αποτυχία λήψης μοντέλου
        debug(f"embedding model load failed: {exc}")
        _MODEL_FAILED = True
        return None
    return _MODEL


def _encode(texts: list[str]):
    model = _get_model()
    if model is None:
        return None
    import numpy as np
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype="float32")


def _row_text(row) -> str:
    el = getattr(row, "description_path_el", "") or row.description_el or ""
    en = getattr(row, "description_path_en", "") or row.description_en or ""
    return f"{en} {el}".strip()


def _load_or_build_matrix():
    """Φορτώνει/χτίζει τον πίνακα embeddings της ονοματολογίας (cache ανά row_count)."""
    global _MATRIX, _CODES, _ROWCOUNT
    if not available():
        return None
    rc = repo.taric_row_count()
    if _MATRIX is not None and _ROWCOUNT == rc:
        return _MATRIX
    import numpy as np

    path = _embeddings_path()
    if path.is_file():
        try:
            data = np.load(path, allow_pickle=True)
            if int(data["rowcount"]) == rc and len(data["codes"]):
                _MATRIX = data["matrix"]
                _CODES = list(data["codes"])
                _ROWCOUNT = rc
                debug(f"loaded {len(_CODES)} taric embeddings from cache")
                return _MATRIX
        except Exception as exc:  # noqa: BLE001
            debug(f"embedding cache load failed, rebuilding: {exc}")

    rows = repo.all_taric_rows()
    if not rows:
        return None
    codes, texts = [], []
    for r in rows:
        codes.append(r.code)
        texts.append(_row_text(r))
    debug(f"building embeddings for {len(texts)} taric rows (one-off)…")
    matrix = _encode(texts)
    if matrix is None:
        return None
    _MATRIX, _CODES, _ROWCOUNT = matrix, codes, rc
    try:
        np.savez_compressed(path, matrix=matrix, codes=np.asarray(codes), rowcount=rc)
    except Exception as exc:  # noqa: BLE001
        debug(f"embedding cache save failed: {exc}")
    return _MATRIX


def is_cache_ready() -> bool:
    """True αν ο πίνακας embeddings είναι έτοιμος (in-memory ή στο δίσκο, ίδιο row_count)."""
    if not available():
        return False
    if _MATRIX is not None and _ROWCOUNT == repo.taric_row_count():
        return True
    path = _embeddings_path()
    if not path.is_file():
        return False
    try:
        import numpy as np
        with np.load(path, allow_pickle=True) as data:
            return int(data["rowcount"]) == repo.taric_row_count() and len(data["codes"]) > 0
    except Exception:  # noqa: BLE001
        return False


def warm(progress=None) -> bool:
    """Χτίζει (αν χρειάζεται) τον πίνακα embeddings — για κλήση σε background worker.

    Το ΠΡΩΤΟ build είναι ακριβό (encode όλης της ονοματολογίας, λεπτά σε CPU), γι'
    αυτό γίνεται εκτός UI thread ΜΙΑ φορά μετά το import. Μέχρι να ετοιμαστεί, το
    pipeline δουλεύει με FTS (η `semantic_candidates` επιστρέφει [] χωρίς μπλοκάρισμα
    — βλ. `_ready_only`). Επιστρέφει True αν ο πίνακας είναι έτοιμος στο τέλος."""
    if not available():
        return False
    if progress:
        progress("Προετοιμασία εννοιολογικού μοντέλου (embeddings)…")
    _load_or_build_matrix()
    if progress and is_cache_ready():
        progress("Το εννοιολογικό μοντέλο είναι έτοιμο.")
    return is_cache_ready()


def semantic_candidates(query: str, *, top: int = 6, min_score: float = 0.30,
                        build_if_missing: bool = False) -> list:
    """Επιστρέφει [(cosine_score, TaricRow)…] με βάση εννοιολογική ομοιότητα.

    Κενή λίστα αν τα embeddings δεν είναι διαθέσιμα/δεν υπάρχει ονοματολογία. Οι
    βαθμολογίες είναι cosine similarity (0..1) σε normalized διανύσματα.
    """
    query = (query or "").strip()
    if not query or not available():
        return []
    matrix = _load_or_build_matrix()
    if matrix is None or len(_CODES) == 0:
        return []
    import numpy as np

    qv = _encode([query])
    if qv is None:
        return []
    sims = matrix @ qv[0]                       # cosine (normalized εκατέρωθεν)
    order = np.argsort(-sims)[: max(top, 1)]
    by_code = {}
    out = []
    for idx in order:
        score = float(sims[idx])
        if score < min_score:
            break
        code = _CODES[idx]
        if code in by_code:
            continue
        by_code[code] = True
        row = repo.get_taric_row(code)
        # Απόκλεισε section/chapter/intermediate headers (level<4): ποτέ έγκυρη κατάταξη
        # (π.χ. 0900000000 «COFFEE, TEA…»). Ίδιο φίλτρο με το FTS tier.
        if row is not None and not (0 < getattr(row, "level", 0) < 4):
            out.append((score, row))
    return out


def reset_cache() -> None:
    """Καθαρίζει το in-memory cache (π.χ. μετά από νέο import ονοματολογίας)."""
    global _MATRIX, _CODES, _ROWCOUNT
    _MATRIX, _CODES, _ROWCOUNT = None, [], -1
