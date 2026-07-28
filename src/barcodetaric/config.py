"""Ρυθμίσεις εφαρμογής & εντοπισμός data-dir.

Όλα τα δεδομένα του χρήστη (SQLite βάση, μοντέλο ML, ρυθμίσεις, cache TARIC)
ζουν σε έναν φάκελο ανά-χρήστη, ώστε το app να τρέχει χωρίς δικαιώματα admin.
Προτεραιότητα data-dir:
  1. env BARCODETARIC_DATA_DIR
  2. HKCU\\Software\\scanmydata\\BarcodeTaric\\DataDir (γράφεται από τον installer)
  3. %LOCALAPPDATA%\\BarcodeTaric  (Windows)  /  ~/.barcodetaric (άλλα OS)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

APP_NAME = "BarcodeTaric"
REG_PATH = r"Software\scanmydata\BarcodeTaric"

# Προεπιλογές ρυθμίσεων. Το settings.json υπερισχύει, το env υπερισχύει όλων.
DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "dark",
<<<<<<< HEAD
    # OpenRouter πρώτο (δωρεάν :free μοντέλα με key). Το Groq μένει ως επιλογή αλλά
    # θέλει login/κλειδί που δεν είναι πάντα διαθέσιμο. Τα no-key (pollinations/
    # duckduckgo) χρεώνουν/περιορίζονται πλέον (402/429) — έσχατο fallback.
    "ai_provider_order": ["custom", "openrouter", "groq", "duckduckgo", "pollinations"],
    "openrouter_model": "meta-llama/llama-3.3-70b-instruct:free",
    "openrouter_api_key": "",
    # Custom OpenAI-compatible endpoint (π.χ. τοπικό ollama μέσω cloudflare tunnel).
    # Δηλώνεις μόνο το URL (base ή πλήρες /v1/chat/completions)· key προαιρετικό.
    "custom_ai_url": "",
    "custom_ai_key": "",
    "custom_ai_model": "llama3.1",
=======
    "ai_provider_order": ["openrouter", "custom", "duckduckgo", "pollinations"],
    # Το free-model landscape του OpenRouter αλλάζει· κράτα ένα ΕΝΕΡΓΟ default.
    # (το παλιό llama-3.3-70b:free αποσύρθηκε -> 404). Δες settings_page «Λήψη δωρεάν μοντέλων».
    "openrouter_model": "openai/gpt-oss-20b:free",
    "openrouter_api_key": "",
    # Custom OpenAI-συμβατό endpoint (μελλοντικό/προαιρετικό): base URL + model + key.
    # Αν συμπληρωθεί το custom_ai_base_url, ο provider «custom» γίνεται διαθέσιμος.
    "custom_ai_base_url": "",   # π.χ. https://my-host/v1  ή  …/v1/chat/completions
    "custom_ai_model": "",      # π.χ. qwen2.5:7b (Ollama μέσω Cloudflare tunnel)
    "custom_ai_api_key": "",
    "custom_ai_timeout": 90,    # local LLM αργεί στο πρώτο token
>>>>>>> b69f1c064e06f3062b3591fa58b396eb91ebe117
    "google_cse_api_key": "",
    "google_cse_id": "",
    # SearXNG meta-search (self-host ή public instance με JSON API ενεργό).
    "searxng_url": "",          # π.χ. https://searx.example.org  ή  http://127.0.0.1:8888
    # OpenSERP: τοπικός server (headless browser) για πραγματικά Google αποτελέσματα χωρίς API key
    # — github.com/karust/openserp. Αν τρέχει, μπορείς να τον βάλεις στη σειρά ως «openserp».
    "openserp_url": "http://127.0.0.1:7000",
    "openserp_engine": "google",
<<<<<<< HEAD
    "openserp_timeout": 45,      # ο headless browser είναι αργός στο πρώτο query
    # SearXNG: self-hosted μετα-μηχανή (πολλές μηχανές μαζί, χωρίς key). Ιδανικό στο
    # μηχάνημα του τοπικού LLM. Απαιτεί `format: json` στο settings.yml του SearXNG.
    "searxng_url": "",
    "searxng_timeout": 15,
    # Σειρά web tiers. Το googlesearch-python είναι ΑΡΓΟ & rate-limited (κάνει sleep
    # μεταξύ requests) — γι' αυτό ΔΕΝ είναι πρώτο. Προτεραιότητα: SearXNG -> OpenSERP
    # (headless browser) -> Brave (επίσημο API) -> Google CSE -> DuckDuckGo ->
    # googlesearch (έσχατο, αργό).
    "web_search_order": ["searxng", "openserp", "brave", "google_cse", "duckduckgo", "googlesearch"],
    # Δωρεάν διαδικτυακή μετάφραση EL<->EN ΧΩΡΙΣ LLM. Το MyMemory (χωρίς key) έχει
    # μνήμη ΕΕ/ΟΗΕ — ιδανικό για τελωνειακό λεξιλόγιο. Με email ανεβαίνει το όριο.
    "translation_provider_order": ["mymemory", "libretranslate"],
    "mymemory_email": "",           # προαιρετικό: 5000 -> 50000 chars/μέρα
    "libretranslate_url": "",       # προαιρετικό self-hosted/public instance
    "libretranslate_api_key": "",
    # Βασική γλώσσα κατάταξης: τα αγγλικά δίνουν καλύτερα αποτελέσματα (η ΕΕ CN/HS
    # ονοματολογία είναι τυποποιημένη στα αγγλικά). Μεταφράζουμε το query σε EN.
    "classify_in_english": True,
    "brave_api_key": "",            # Brave Search API (2000 δωρεάν queries/μήνα)
    "ocrspace_api_key": "",         # ocr.space free tier (OCR ετικέτας από φωτό προϊόντος)
    # Τοπικά (offline) πολύγλωσσα embeddings για ΕΝΝΟΙΟΛΟΓΙΚΗ αντιστοίχιση (νόημα, όχι
    # μόνο λέξεις). Θέλει `pip install -e ".[semantic]"` (sentence-transformers). Αν
    # λείπει, το tier παρακάμπτεται σιωπηλά.
    "semantic_enabled": True,
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
=======
    "openserp_timeout": 45,     # ο headless browser του OpenSERP αργεί στο πρώτο query
    # headless = πραγματικό Chrome μέσω Selenium (παρακάμπτει το Google scraping-block).
    "chrome_binary": "",        # προαιρετικό override διαδρομής chrome.exe
    "headless_headed": False,   # true = ορατό παράθυρο Chrome (λιγότερο ανιχνεύσιμο ως bot)
    # Χρήση του ΠΡΑΓΜΑΤΙΚΟΥ προφίλ Chrome του υπολογιστή (cookies/consent/login) ώστε η Google
    # να μη σε περνά για bot. Άφησε κενό για καθαρό προφίλ. π.χ. %LOCALAPPDATA%\Google\Chrome\User Data
    "chrome_user_data_dir": "",
    "chrome_profile": "",       # π.χ. "Default" ή "Profile 1" (μαζί με το user_data_dir)
    "web_search_order": ["searxng", "duckduckgo", "headless", "googlesearch", "google_cse"],
>>>>>>> b69f1c064e06f3062b3591fa58b396eb91ebe117
    "ml_confidence_threshold": 0.55,
    "ml_min_samples": 40,
    "ml_autoretrain_every": 25,
    "auto_update_taric": True,   # έλεγχος/ενημέρωση ονοματολογίας από ΕΕ στην εκκίνηση
    "business_portal_key": "",   # GEMI opendata (ΑΦΜ -> στοιχεία εταιρείας)
    "groq_api_key": "",          # δωρεάν key από console.groq.com (χωρίς κάρτα)
    "groq_model": "llama-3.3-70b-versatile",
}


def _registry_data_dir() -> Path | None:
    if sys.platform != "win32":
        return None
    try:
        import winreg  # type: ignore

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            value, _ = winreg.QueryValueEx(key, "DataDir")
            if value:
                return Path(value)
    except OSError:
        return None
    return None


def data_dir() -> Path:
    env = os.getenv("BARCODETARIC_DATA_DIR")
    if env:
        base = Path(env)
    else:
        reg = _registry_data_dir()
        if reg is not None:
            base = reg
        elif sys.platform == "win32":
            local = os.getenv("LOCALAPPDATA") or str(Path.home())
            base = Path(local) / APP_NAME
        else:
            base = Path.home() / ".barcodetaric"
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return data_dir() / "barcodetaric.db"


def model_path() -> Path:
    return data_dir() / "model.joblib"


def settings_path() -> Path:
    return data_dir() / "settings.json"


def dotenv_path() -> Path:
    return data_dir() / ".env"


class Settings:
    """Απλός φορτωτής/αποθηκευτής ρυθμίσεων με fallback στα env vars."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(DEFAULT_SETTINGS)
        self._load()

    def _load(self) -> None:
        path = settings_path()
        if path.is_file():
            try:
                stored = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(stored, dict):
                    self._data.update(stored)
            except (json.JSONDecodeError, OSError):
                pass
        _load_dotenv(dotenv_path())

    def get(self, key: str, default: Any = None) -> Any:
        # env override (π.χ. OPENROUTER_API_KEY) υπερισχύει του settings.json
        env_key = key.upper()
        if os.getenv(env_key):
            return os.getenv(env_key)
        return self._data.get(key, DEFAULT_SETTINGS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def save(self) -> None:
        settings_path().write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Κράτα και τα κλειδιά AI στο process environment ώστε να τα δει η μηχανή.
        for env_key in ("openrouter_api_key", "google_cse_api_key", "google_cse_id",
                        "groq_api_key", "custom_ai_api_key"):
            val = self._data.get(env_key)
            if val:
                os.environ[env_key.upper()] = str(val)

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# Singleton, ώστε όλα τα modules να μοιράζονται τις ίδιες ρυθμίσεις.
SETTINGS = Settings()
