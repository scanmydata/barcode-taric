"""Έλεγχος ενημερώσεων για την επίσημη ΕΕ ονοματολογία (μέσω CIRCABC)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .. import repo
from . import circabc


@dataclass
class UpdateStatus:
    current_version: str
    current_rows: int
    latest_version: Optional[str]
    update_available: bool
    message: str


def check_for_updates(progress: Optional[Callable[[str], None]] = None) -> UpdateStatus:
    meta = repo.taric_meta()
    current_version = str((meta or {}).get("version") or "—")
    current_rows = int((meta or {}).get("row_count") or 0)

    latest = None
    try:
        latest = circabc.latest_available_version(progress)
    except Exception:  # noqa: BLE001 - δικτυακό/parse σφάλμα -> άγνωστο
        latest = None

    update_available = bool(latest and latest != current_version)
    if current_rows == 0:
        message = "Δεν έχει γίνει ακόμη import ΕΕ ονοματολογίας — τρέξτε «Αυτόματη ενημέρωση από ΕΕ»."
    elif latest is None:
        message = f"Τοπική έκδοση: {current_version} ({current_rows} κωδικοί). Αδυναμία ελέγχου CIRCABC."
    elif update_available:
        message = f"Διαθέσιμη νεότερη έκδοση: {latest} (τρέχουσα: {current_version})."
    else:
        message = f"Η ονοματολογία είναι ενήμερη ({current_version}, {current_rows} κωδικοί)."

    return UpdateStatus(current_version=current_version, current_rows=current_rows,
                        latest_version=latest, update_available=update_available, message=message)
