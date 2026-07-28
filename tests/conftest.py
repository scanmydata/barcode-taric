"""Κοινό pytest setup: απομονωμένο data-dir ανά test session."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def _isolated_data_dir():
    tmp = Path(tempfile.mkdtemp(prefix="barcodetaric_test_"))
    os.environ["BARCODETARIC_DATA_DIR"] = str(tmp)
    # Force settings/db να ξαναδιαβάσουν το νέο dir.
    from barcodetaric import db
    db.init_db()

    # ΚΡΙΣΙΜΟ: το SETTINGS singleton δημιουργήθηκε στο import ΠΡΙΝ οριστεί το isolated dir,
    # οπότε κουβαλά το ΠΡΑΓΜΑΤΙΚΟ settings.json (π.χ. OpenRouter key). Χωρίς εξουδετέρωση,
    # κάποιος συνδυασμός tests καλεί ΑΛΗΘΙΝΟ AI/web -> το suite «κρεμάει» σε network.
    # Μηδενίζουμε providers/keys ώστε ai_available()=False & καμία δικτυακή κλήση by default·
    # όσα tests θέλουν AI κάνουν monkeypatch.
    for env_key in ("OPENROUTER_API_KEY", "CUSTOM_AI_API_KEY", "GROQ_API_KEY",
                    "GOOGLE_CSE_API_KEY", "GOOGLE_CSE_ID", "BUSINESS_PORTAL_KEY"):
        os.environ.pop(env_key, None)
    from barcodetaric.config import SETTINGS
    SETTINGS.set("ai_provider_order", [])
    # Μόνο searxng (χωρίς url -> skip, καμία δικτυακή κλήση). ΟΧΙ headless (selenium εγκατεστημένο
    # -> θα άνοιγε Chrome & θα κρέμαγε το suite) ούτε duckduckgo (αληθινό network).
    SETTINGS.set("web_search_order", ["searxng"])
    for key in ("openrouter_api_key", "custom_ai_base_url", "searxng_url", "openserp_url",
                "groq_api_key", "business_portal_key", "google_cse_api_key", "google_cse_id"):
        SETTINGS.set(key, "")
    yield tmp
