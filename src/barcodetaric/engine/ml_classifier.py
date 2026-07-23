"""Τοπικός ML ταξινομητής περιγραφής -> TARIC (scikit-learn, δωρεάν, offline).

Μαθαίνει από τα επιβεβαιωμένα (verified=1) ζεύγη της βάσης. Όσο μεγαλώνει το
dataset, αναλαμβάνει όλο και περισσότερες αποφάσεις χωρίς κλήση LLM.

Σχεδίαση: TF-IDF (word + char n-grams, EL+EN) -> LogisticRegression.
Δύο στάδια: μοντέλο πλήρους TARIC κωδικού + μοντέλο HS4 (heading). Αν το πλήρες
μοντέλο έχει χαμηλή βεβαιότητα, πέφτουμε στο HS4 (τουλάχιστον σωστό κεφάλαιο).
Το ίδιο interface θα δεχτεί μελλοντικά embeddings αντί για TF-IDF.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import SETTINGS, model_path
from .. import repo


@dataclass
class MLPrediction:
    code: str
    hs4: str
    confidence: float
    stage: str  # "taric" | "hs4"


def _feature_text(description_el: str, description_en: str, barcode: str = "",
                  brand: str = "", quantity: str = "", categories: str = "") -> str:
    prefix = re.sub(r"\D", "", barcode)[:7]  # GS1 prefix ~ χώρα/κατασκευαστής
    return " ".join(p for p in (
        description_el, description_en, brand, quantity, categories,
        f"gs1_{prefix}" if prefix else "",
    ) if p)


def _build_pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline([
        ("tfidf", TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), min_df=1, sublinear_tf=True,
            lowercase=True, strip_accents="unicode",
        )),
        ("clf", LogisticRegression(max_iter=1000, C=4.0, class_weight="balanced")),
    ])


class TaricML:
    """Wrapper γύρω από τα δύο pipelines με persistence σε joblib."""

    def __init__(self) -> None:
        self.taric_model = None
        self.hs4_model = None
        self.n_samples = 0

    # ------------------------------------------------------------- training ----
    def train(self) -> dict:
        try:
            import sklearn  # noqa: F401
            import joblib  # noqa: F401
        except ImportError:
            return {"trained": False, "reason": "missing_dependencies",
                    "message": "Λείπουν οι βιβλιοθήκες scikit-learn/joblib."}
        rows = repo.verified_training_rows()
        texts, taric_labels, hs4_labels = [], [], []
        for r in rows:
            code = (r.get("taric_code") or "").strip()
            if not code:
                continue
            texts.append(_feature_text(
                r.get("description_el") or "", r.get("description_en") or "",
                r.get("barcode") or "", r.get("brand") or "", r.get("quantity") or "",
                r.get("categories") or ""))
            taric_labels.append(code)
            hs4_labels.append((r.get("hs4") or code[:4]).strip())

        self.n_samples = len(texts)
        min_samples = int(SETTINGS.get("ml_min_samples", 40))
        if self.n_samples < max(4, min_samples):
            return {"trained": False, "reason": "insufficient_samples",
                    "n_samples": self.n_samples, "min_samples": min_samples}

        result = {"trained": False, "n_samples": self.n_samples}

        # HS4 μοντέλο (πιο εύκολο, λιγότερες κλάσεις)
        if len(set(hs4_labels)) >= 2:
            self.hs4_model = _build_pipeline()
            self.hs4_model.fit(texts, hs4_labels)
            result["hs4_classes"] = len(set(hs4_labels))

        # Πλήρες TARIC μοντέλο (χρειάζεται >=2 κλάσεις με δεδομένα)
        if len(set(taric_labels)) >= 2:
            self.taric_model = _build_pipeline()
            self.taric_model.fit(texts, taric_labels)
            result["taric_classes"] = len(set(taric_labels))
            result["trained"] = True
        elif self.hs4_model is not None:
            result["trained"] = True

        result["cv_accuracy"] = self._cross_val(texts, taric_labels)
        self.save()
        repo.set_ml_meta(model_version="tfidf-logreg-v1", n_samples=self.n_samples,
                         cv_accuracy=result.get("cv_accuracy", 0.0), algo="TF-IDF + LogisticRegression")
        return result

    def _cross_val(self, texts: list[str], labels: list[str]) -> float:
        try:
            from collections import Counter
            from sklearn.model_selection import cross_val_score
            counts = Counter(labels)
            if len(counts) < 2 or min(counts.values()) < 2 or len(texts) < 10:
                return 0.0
            folds = min(3, min(counts.values()))
            scores = cross_val_score(_build_pipeline(), texts, labels, cv=folds)
            return float(scores.mean())
        except Exception:  # noqa: BLE001
            return 0.0

    # ------------------------------------------------------------- predict ----
    def predict(self, description_el: str, description_en: str = "", barcode: str = "",
                brand: str = "", quantity: str = "", categories: str = "") -> Optional[MLPrediction]:
        if self.taric_model is None and self.hs4_model is None:
            return None
        text = _feature_text(description_el, description_en, barcode, brand, quantity, categories)
        if not text.strip():
            return None
        threshold = float(SETTINGS.get("ml_confidence_threshold", 0.55))

        if self.taric_model is not None:
            code, conf = self._top(self.taric_model, text)
            if code and conf >= threshold:
                return MLPrediction(code=code, hs4=code[:4], confidence=conf, stage="taric")

        if self.hs4_model is not None:
            hs4, conf = self._top(self.hs4_model, text)
            if hs4 and conf >= threshold:
                return MLPrediction(code="", hs4=hs4, confidence=conf, stage="hs4")
        return None

    @staticmethod
    def _top(model, text: str) -> tuple[str, float]:
        proba = model.predict_proba([text])[0]
        classes = model.classes_
        best_idx = int(proba.argmax())
        return str(classes[best_idx]), float(proba[best_idx])

    # ---------------------------------------------------------- persistence ----
    def save(self, path: Path | None = None) -> None:
        import joblib
        joblib.dump(
            {"taric_model": self.taric_model, "hs4_model": self.hs4_model,
             "n_samples": self.n_samples},
            path or model_path(),
        )

    @classmethod
    def load(cls, path: Path | None = None) -> "TaricML":
        obj = cls()
        p = path or model_path()
        if Path(p).is_file():
            try:
                import joblib
                data = joblib.load(p)
                obj.taric_model = data.get("taric_model")
                obj.hs4_model = data.get("hs4_model")
                obj.n_samples = data.get("n_samples", 0)
            except Exception:  # noqa: BLE001 - λείπει joblib/sklearn ή φθαρμένο αρχείο
                pass
        return obj

    def is_ready(self) -> bool:
        return self.taric_model is not None or self.hs4_model is not None


# Cache μοντέλου (φορτώνεται μία φορά ανά process).
_CACHED: Optional[TaricML] = None


def get_model(reload: bool = False) -> TaricML:
    global _CACHED
    if _CACHED is None or reload:
        _CACHED = TaricML.load()
    return _CACHED


def retrain() -> dict:
    global _CACHED
    model = TaricML()
    result = model.train()
    _CACHED = model
    return result
