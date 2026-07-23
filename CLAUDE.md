# CLAUDE.md — οδηγός για μελλοντικούς agents

Αυτό το αρχείο φορτώνεται αυτόματα από το Claude Code. Περιγράφει **τι είναι** το
project, **πώς λειτουργεί** και **τι πρέπει να προσέχεις** πριν αλλάξεις κώδικα.

## Τι είναι

`BarcodeTaric` — τοπικό **desktop app (PySide6/Qt6)** για ελληνικά τελωνειακά/λογιστικά:
διαχείριση **πελατολογίου** και αντιστοίχιση **barcode → περιγραφή προϊόντος → κωδικός TARIC**
της ΕΕ, με **export** ανά πελάτη. Στόχος: εντελώς **δωρεάν** λειτουργία (free AI + τοπικό ML)
και **offline** αντιστοίχιση μετά το import της επίσημης ΕΕ ονοματολογίας.

Είναι **ολική ανακατασκευή** ενός παλιότερου Flask+Tkinter prototype. Το layout/installer
ακολουθεί το reference project `../timologio-downloader` (PySide6 + PyInstaller + Inno Setup).

## Εντολές

```bash
# dev run (GUI)
.venv\Scripts\python -m barcodetaric.gui
# ή headless-safe: QT_QPA_PLATFORM=offscreen για smoke test χωρίς οθόνη

# CLI (χωρίς GUI)
python -m barcodetaric.cli import-taric            # φόρτωση builtin seed ονοματολογίας
python -m barcodetaric.cli import-taric FILE|URL   # επίσημο CN αρχείο/URL
python -m barcodetaric.cli resolve "coffee" --no-ai
python -m barcodetaric.cli train                   # εκπαίδευση τοπικού ML

# tests (15, όλα offline/ντετερμινιστικά)
.venv\Scripts\python -m pytest
# ΣΗΜΑΝΤΙΚΟ σε Windows: πρόθεσε PYTHONUTF8=1 όταν το script τυπώνει ελληνικά (cp1252 stdout).

# local installer (Windows, per-user, χωρίς admin)
powershell -ExecutionPolicy Bypass -File installer\build.ps1
```

Το venv είναι στο `.venv/`. Deps στο `pyproject.toml` (hatchling build backend).

## Αρχιτεκτονική (layered, `src/barcodetaric/`)

```
config.py     data-dir resolution (env > HKCU registry > %LOCALAPPDATA%), Settings singleton (SETTINGS)
db.py         SQLite connection + schema + FTS5 (standalone folded tables)
models.py     dataclasses: Client, CatalogItem, ClientItem, TaricRow, TaricCandidate
repo.py       ΟΛΑ τα SQL/CRUD + FTS maintenance + search. Καμία επιχειρησιακή λογική αλλού δεν αγγίζει SQL.
cli.py        console entry (project.scripts: barcodetaric)

engine/       καθαρή μηχανή (χωρίς Qt, χωρίς SQL εκτός μέσω repo)
  http_util.py     urllib helpers, text normalisation, stem_token (EL+EN light stemmer)
  ai.py            provider chain: openrouter(:free)->duckduckgo->pollinations, groq stub. chat()/translate()/
                   infer_product()/rank_taric()/rationalize(). Διαβάζει SETTINGS.
  web_search.py    Google results 3 tiers: googlesearch-python -> Google CSE API -> DuckDuckGo HTML.
  barcode_sources.py  multi-source lookup + EAN13 helpers. fetch_product() = AI/web -> OFF/UPC/scrapers.
  translate.py     EL<->EN (μέσω ai) + product-name quality gates (sanitize_name).
  ml_classifier.py τοπικό ML (TF-IDF + LogisticRegression), TaricML (train/predict/save/load), get_model()/retrain().
  taric_match.py   ΕΝΟΡΧΗΣΤΡΩΤΗΣ αντιστοίχισης (βλ. «Pipeline» πιο κάτω). MatchResult.
  resolve.py       top-level: resolve_barcode()/resolve_description() -> ResolveResult (περιγραφή EL/EN + TARIC).

  business_lookup.py ΑΦΜ -> στοιχεία εταιρείας μέσω GEMI opendata (opendata-api.businessportal.gr,
                   header api_key = SETTINGS['business_portal_key']). lookup_by_afm().

taric/
  importer.py   import ΕΕ CN: parse_file() (xml/csv/tsv/xlsx/zip) + parse_nomenclature() (CIRCABC
                EL/EN xlsx με ΙΕΡΑΡΧΙΚΟ path context). import_from_file/url, import_seed.
  circabc.py    ΑΥΤΟΜΑΤΗ λήψη/ενημέρωση από επίσημο CIRCABC (node 64db9d0f-…): TARIC data ->
                <έτος> -> <μήνας> -> «Nomenclature EL/EN.xlsx». auto_import(), find_latest_nomenclature().
                API: /service/circabc/... (guest). Download: /d/d/workspace/SpacesStore/{id}/{name}.
  updates.py    check_for_updates() -> UpdateStatus (σύγκριση έκδοσης με το τελευταίο CIRCABC snapshot).

excel/
  reader.py     read_codebook() — import κωδικολογίου πελάτη με auto-detect στηλών.
  exporter.py   export() — xlsx/csv κωδικολογίου πελάτη με τους matched TARIC.

gui/            PySide6 UI (layout timologio: sidebar + QStackedWidget + dark/light QSS)
  app.py        QApplication bootstrap (init_db, theme, MainWindow)
  main_window.py shell + navigation (PAGE_INDEX). Signals: clients->codebook, back, theme.
  side_menu.py  sidebar (pure emitter triggered(name))
  theme.py      Palette dataclass (DARK/LIGHT) + build() -> QSS. CURRENT proxy.
  widgets.py    Card, StatTile, h1/h2/muted/section_label
  workers.py    run_async() — γενικός QThread worker (progress/finished/failed). Κρατά refs στο parent._active_workers.
  clients_page / client_dialog / codebook_page / catalog_page / taric_page / settings_page
```

**Import κανόνας:** `repo` importάρει `engine.http_util` (μόνο stdlib helpers). Τα υπόλοιπα
engine modules importάρουν `.. import repo`. Δεν υπάρχει κύκλος γιατί `http_util` δεν αγγίζει repo.
Κράτα το έτσι — μη βάλεις `import repo` μέσα στο `http_util`.

## Database schema (SQLite + FTS5, ένα αρχείο ανά-χρήστη)

- `clients` — πελάτες (name, vat/ΑΦΜ, email, phone, address, notes).
- `catalog` — κεντρική βάση γνώσης barcode→περιγραφή→TARIC. `barcode` UNIQUE. Πεδία: description_el/en,
  taric_code, hs4, taric_description, confidence, ai_rationale, `taric_source`, `verified`, source.
- `client_items` — κωδικολόγιο ανά πελάτη. UNIQUE(client_id, barcode). Ίδια «TARIC» πεδία + catalog_id FK.
- `taric_nomenclature` — επίσημη ΕΕ ονοματολογία (code, level, parent_code, description_el/en, hs4, ...).
- `taric_meta` / `ml_meta` — μία γραμμή (id=1) με version/imported_at/row_count και model stats.
- `catalog_fts`, `taric_nomenclature_fts` — **standalone** FTS5 tables με ΕΝΑ `text` column (βλ. gotcha #1).

`taric_source` τιμές: `catalog | ml | fts | ai | manual | web`. `verified=1` σημαίνει «training label».

## Pipeline αντιστοίχισης TARIC (`taric_match.match()`) — σειρά αυξανόμενου κόστους

1. **catalog** — αν το barcode υπάρχει ήδη στο `catalog` με taric_code → επιστροφή αμέσως.
2. **ml** — `ml_classifier.get_model().predict()`. Αν stage=="taric" & confidence ≥ threshold → επιστροφή **χωρίς AI**.
3. **fts** — `repo.search_taric()` (FTS πάνω στο ΙΕΡΑΡΧΙΚΟ path) → `_score()` **IDF-σταθμισμένο** (κοινές
   λέξεις νερό/water/other μετράνε λίγο, σπάνιες coffee/mineral πολύ· prefix-aware + stemmed) → top υποψήφιοι.
4. **ai** — μόνο αν υπάρχουν υποψήφιοι & `ai.ai_available()`: `ai.rank_taric()` επιλέγει + δίνει rationalization.
5. fallback: κορυφαίος FTS υποψήφιος χωρίς AI.

Το `match()` δέχεται και brand/quantity/categories (τροφοδοτούν ML features & match text). Η μηχανή
`resolve.resolve_barcode()` περνά barcode → πολλαπλές πηγές (OpenFoodFacts δίνει categories+quantity) →
AI enrichment (αναλυτική περιγραφή με μέγεθος) → match. **Κρίσιμο:** το FTS index περιέχει το πλήρες
γονικό path (π.χ. «ΖΩΑ ΖΩΝΤΑΝΑ > Άλογα > …») ώστε leaf-περιγραφές τύπου «Άλλα» να έχουν context.

Κάθε επιβεβαίωση χρήστη (`verified=1`, από codebook_page) γίνεται training label και τροφοδοτεί το `catalog`.
Έτσι, όσο συσσωρεύονται δεδομένα, το **ML tier (2)** αναλαμβάνει όλο και περισσότερες αποφάσεις και οι AI-κλήσεις πέφτουν.

## AI & web (όλα δωρεάν)

- Provider chain στο `ai.py`, σειρά από `SETTINGS["ai_provider_order"]`. **OpenRouter** (χρειάζεται
  `OPENROUTER_API_KEY`, **ΜΟΝΟ** `:free` μοντέλα — το `_ensure_free()` προσθέτει αυτόματα το suffix) →
  **DuckDuckGo** chat → **Pollinations** (χωρίς key). **Groq** stub (`groq_enabled`, μελλοντικό).
- `ai.list_free_models()` (φιλτράρει pricing==0 από OpenRouter), `ai.test_providers()` (debugger).
- **Logging/debugger** στο `logs.py`: rotating αρχείο `data-dir/logs/barcodetaric.log` + in-memory ring
  buffer. Το `http_util.debug()` γράφει κι εκεί. Στο settings_page: «Έλεγχος AI providers» + άνοιγμα log.
- Web results στο `web_search.py`: googlesearch-python → Google CSE (αν key+cse_id) → DuckDuckGo HTML.
- Keys/ρυθμίσεις: αποθηκεύονται στο `settings.json` (data-dir) + env vars, μέσω `SETTINGS.save()`.
  Το env var υπερισχύει του settings.json (π.χ. `OPENROUTER_API_KEY`).

## ML (scikit-learn, τοπικό, δωρεάν)

- Features: `description_el + description_en + gs1_<barcode-prefix>` → TF-IDF (word 1-2grams).
- Δύο μοντέλα: πλήρες TARIC code + HS4 heading. Χαμηλή βεβαιότητα στο πλήρες → πέφτει στο HS4.
- Εκπαίδευση από `repo.verified_training_rows()` (verified=1 σε client_items ∪ catalog). Απαιτεί
  `ml_min_samples` (default 40· στα tests μειώνεται). Persistence: `model.joblib` στο data-dir + `ml_meta`.
- Graceful degradation: αν λείπουν sklearn/joblib, το ML tier απλώς παρακάμπτεται (δεν σκάει).

## TARIC import (επίσημη ΕΕ CN)

- Δεν υπάρχει δωρεάν επίσημο REST API της ΕΕ. Κατεβάζουμε & κάνουμε parse τοπικά.
- `importer.parse_file()` είναι **format-flexible** (xml/csv/tsv/xlsx/zip) με auto-detect στηλών code/description
  και ανίχνευση γλώσσας (EL vs EN) από περιεχόμενο. Πηγή: data.europa.eu «Combined Nomenclature <έτος>».
- `import_seed()` φορτώνει 16 HS4 headings ώστε το app να δουλεύει από την πρώτη στιγμή (demo/tests).
  Για πραγματική κάλυψη ο χρήστης κάνει import το επίσημο CN αρχείο από τη σελίδα TARIC.

## ΣΗΜΑΝΤΙΚΑ gotchas (μη τα σπάσεις)

1. **FTS + ελληνικοί τόνοι.** Ο SQLite `unicode61` tokenizer (ακόμη και `remove_diacritics 2`) **δεν**
   αφαιρεί precomposed ελληνικούς τόνους (`ά`,`έ`,…). Γι' αυτό τα FTS tables είναι **standalone** και το
   `repo` γράφει σε αυτά **folded** κείμενο (πεζά, χωρίς τόνους) μέσω `_fold()`. Τα queries (`_fts_query`)
   επίσης αφαιρούν τόνους + κάνουν stem + βάζουν `*` (prefix). Αν αλλάξεις το ένα, άλλαξε και το άλλο,
   αλλιώς το ελληνικό matching σπάει σιωπηλά.
2. **Stemming** (`http_util.stem_token`) είναι σκόπιμα light (ενικός/πληθυντικός: νερό/νερά, water/waters).
   Χρησιμοποιείται και στο `_fts_query` (retrieval) και στο `taric_match._tokens` (scoring). Κράτα τα συνεπή.
3. **Windows stdout = cp1252.** Τα `print()` ελληνικών σε script σκάνε χωρίς `PYTHONUTF8=1`. Δεν αφορά το GUI.
4. **Qt threads.** Οτιδήποτε δικτυακό/αργό (barcode lookup, match-all, import, retrain) τρέχει μέσω
   `workers.run_async()` σε QThread — ΠΟΤΕ μη καλέσεις network/AI στο UI thread. Το worker περνά αυτόματα
   `progress` callback αν η συνάρτηση το δέχεται.
5. **Test isolation.** Το `SETTINGS` είναι singleton και το ML model έχει module-level cache (`_CACHED`).
   Tests που εκπαιδεύουν ML αλλάζουν global state· το `test_taric_match` το μηδενίζει ρητά. Αν προσθέσεις
   ML-εξαρτώμενα tests, κάνε reset threshold + `ml_classifier._CACHED`.
6. **data-dir.** Όλα τα runtime δεδομένα ζουν στο `%LOCALAPPDATA%\BarcodeTaric` (ή `BARCODETARIC_DATA_DIR`).
   Τα tests/e2e χρησιμοποιούν απομονωμένο dir μέσω αυτού του env var (βλ. `tests/conftest.py`).
7. **openpyxl read_only lock (Windows).** Το `load_workbook(read_only=True)` κρατά το αρχείο ανοιχτό·
   ΠΑΝΤΑ κάλεσε `wb.close()` πριν διαγράψεις temp αρχεία (βλ. `importer._parse_nomenclature_sheet`),
   αλλιώς `PermissionError: WinError 32`.
8. **Schema migrations.** Νέες στήλες προστίθενται μέσω `db._ensure_columns()` (ALTER-if-missing) ώστε
   υπάρχουσες βάσεις χρηστών να μη χάνουν δεδομένα. Πρόσθεσε εκεί κάθε νέα στήλη (catalog/client_items/
   taric_nomenclature έχουν ήδη migrations για brand/quantity/categories & description_path_el/en).
9. **Αυτόματη ενημέρωση.** Με `SETTINGS["auto_update_taric"]` (default True), στην εκκίνηση το
   `main_window._startup_taric_check()` ελέγχει το CIRCABC και κατεβάζει background αν λείπει/παλιά.

## Installer

`installer/`: `barcodetaric.spec` (PyInstaller one-dir, όχι one-file), `barcodetaric.iss` (Inno Setup,
`PrivilegesRequired=lowest`, HKCU `DataDir`/`InstallDir`, ελληνικός wizard), `build.ps1` (venv→icon→
PyInstaller→ISCC), `make_icon.py` (φτιάχνει icon.ico με PySide6, χωρίς εξωτερικά assets).

## Γνωστά όρια / μελλοντικά

- Το builtin seed είναι μικρό — η πραγματική ακρίβεια εξαρτάται από import του πλήρους CN.
- DuckDuckGo chat endpoint είναι ασταθές (χρειάζεται vqd token)· η αξιόπιστη AI διαδρομή είναι OpenRouter.
- Το ML ξεκινά cold (χρειάζεται verified δεδομένα)· μέχρι τότε κυριαρχεί το FTS+AI.
- Μελλοντικά: embeddings αντί TF-IDF (ίδιο interface στο `ml_classifier.py`), TARIC 10-digit daily extraction.
```
