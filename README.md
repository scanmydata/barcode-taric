# BarcodeTaric

Τοπικό desktop app (PySide6) για **πελατολόγιο** και αντιστοίχιση **barcode → περιγραφή → TARIC**.

## Τι κάνει

- **Πελατολόγιο με CRUD** — διαχείριση πελατών, ανά πελάτη δικό του κωδικολόγιο.
- **Import κωδικολογίου από Excel/CSV** (auto-detect στηλών barcode/περιγραφή) ή **add-by-barcode**
  με αναζήτηση σε πολλαπλές πηγές + πραγματικά **web results** (SearXNG → googlesearch → Google CSE → DuckDuckGo)
  και AI web-inference όταν δεν βρίσκεται περιγραφή.
- **Αυτόματη άντληση στοιχείων εταιρείας από ΑΦΜ** (ΓΕΜΗ) — μόλις συμπληρωθεί 9ψήφιος ΑΦΜ στη φόρμα πελάτη.
- **Κεντρική βάση γνώσης** (barcode → περιγραφή → TARIC) με γρήγορο full-text search, που μεγαλώνει με τη χρήση.
- **Έγκυρο TARIC** από την **επίσημη ΕΕ ονοματολογία** (Combined Nomenclature) — import + έλεγχος ενημερώσεων,
  offline matching με FTS + AI ranking/rationalization.
- **English-first κατάταξη** — η επίσημη ονοματολογία CN/HS είναι τυποποιημένη στα Αγγλικά, οπότε η μηχανή
  μεταφράζει το query στα **Αγγλικά πριν την αντιστοίχιση** (μέσω δωρεάν μεταφραστικού, χωρίς LLM) για καλύτερη ακρίβεια.
- **Εννοιολογική αντιστοίχιση** (προαιρετικό, τοπικά **embeddings**) — ταιριάζει βάσει **νοήματος**
  (συνώνυμα/παραφράσεις), όχι μόνο λέξεων· offline & δωρεάν με `pip install -e ".[semantic]"`.
- **OCR ετικέτας** (προαιρετικό) — όταν οι πηγές barcode δεν δίνουν αξιόπιστη ονομασία αλλά υπάρχει φωτό
  προϊόντος, διαβάζεται το κείμενο της ετικέτας για να αναγνωριστεί **τι είναι** το προϊόν.
- **Τοπικό μοντέλο ML** (scikit-learn) που μαθαίνει από τα **επιβεβαιωμένα** είδη· όσο μεγαλώνει το dataset,
  αναλαμβάνει όλο και περισσότερες αποφάσεις **χωρίς κλήση AI**.
- **Export** κωδικολογίου πελάτη με τους σωστούς TARIC σε Excel/CSV.

## Πώς «ασφαλίζεται» η περιγραφή πριν την κατάταξη

Για να μη γίνονται λάθη τύπου «X water → toilet water (άρωμα)», η ροή διασταυρώνει
πηγές πριν κατατάξει:

1. **Δομημένες πηγές barcode** (OpenFoodFacts/UPC/…) δίνουν υποψήφια ονομασία —
   με φίλτρο που απορρίπτει «σκουπίδια» (τίτλους των ίδιων των sites αναζήτησης).
   Αν λείπει ονομασία αλλά υπάρχει φωτό, γίνεται **OCR** της ετικέτας (αν έχει ρυθμιστεί key).
2. **Παράλληλη αναζήτηση web** για το barcode **και** για την ονομασία (cross-check).
3. Ένα **AI βήμα** «κλειδώνει» σύντομη **ονομασία EL/EN** (μόνο *τι είναι*, όχι
   αναλυτική περιγραφή), αν είναι **προϊόν ή υπηρεσία**, και ένα εσωτερικό
   `customs_hint` (π.χ. *natural mineral water, bottled*) που ξεχωρίζει το νερό
   (2201) από το άρωμα (3303).
4. **Υπηρεσίες/άυλα δεν λαμβάνουν TARIC.** Τα προϊόντα κατατάσσονται με το hint.
5. **Δικλείδα χωρίς AI:** ακόμη κι όταν το LLM δεν είναι διαθέσιμο, η ονομασία
   **διασταυρώνεται με τα web αποτελέσματα** (corroboration score): αν δεν επιβεβαιώνεται
   από κανένα αποτέλεσμα απορρίπτεται ως αναξιόπιστη. Επιπλέον, όταν η πηγή είναι τρόφιμο
   (OpenFoodFacts), η κατάταξη προτιμά τα κεφάλαια τροφίμων/ποτών (01–24), ώστε το «water»
   να μη γίνει άρωμα.

## Δωρεάν AI

Χρησιμοποιεί δωρεάν providers με σειρά (`ai_provider_order`): **OpenRouter** (`:free` μοντέλα,
χρειάζεται API key) → **custom** (προαιρετικό δικό σου endpoint) → **DuckDuckGo** → **Pollinations**.
Το **Groq** υπάρχει ως μελλοντική (απενεργοποιημένη) επιλογή. Τα κλειδιά μπαίνουν από τη σελίδα **Ρυθμίσεις**.

> ⚠️ **Το free-model landscape του OpenRouter αλλάζει** — μοντέλα αποσύρονται και το API επιστρέφει
> `404`. Το app κάνει **auto-fallback** (working → `openai/gpt-oss-20b:free` → `openrouter/free`) και
> «θυμάται» αυτό που δουλεύει. Default: `openai/gpt-oss-20b:free`.

### Επιλογή μοντέλου OpenRouter (Ρυθμίσεις)

Στις **Ρυθμίσεις → Μοντέλο (:free)** διαλέγεις **σε ποιο μοντέλο στέλνονται τα δεδομένα**. Η λίστα
των δωρεάν μοντέλων **ανανεώνεται αυτόματα** κάθε φορά που ανοίγεις τις Ρυθμίσεις (με cache TTL
`free_models_ttl_sec`, default 6h) — φιλτραρισμένη σε chat/instruct μοντέλα και ταξινομημένη με τα
καλύτερα πρώτα. Κουμπιά: **«Ανανέωση λίστας»** (άμεση λήψη, αγνοεί το cache) και **«Έξυπνη επιλογή»**
(δοκιμάζει τα κορυφαία & κρατά ένα που όντως απαντά). Αν το αποθηκευμένο μοντέλο αποσυρθεί,
επισημαίνεται και επιλέγεται αυτόματα διαθέσιμο.

### Μαζικό rationalization (πολλά προϊόντα ανά prompt)

Η μαζική αντιστοίχιση στέλνει **N προϊόντα σε ΜΙΑ κλήση AI** (`rank_taric_batch`, default 20/κλήση)
αντί για μία κλήση ανά προϊόν. Το prompt είναι **adaptive**:

- Όταν οι υποψήφιοι κωδικοί **επαναλαμβάνονται** μεταξύ προϊόντων (τυπικό σε μαζικό import ομοειδών),
  στέλνεται **μία φορά ένα κοινό «CODEBOOK»** (το σχετικό slice της ονοματολογίας: `κωδικός = επίσημη
  περιγραφή`) και κάθε προϊόν αναφέρει μόνο τους επιτρεπτούς κωδικούς του → **~50% λιγότερα tokens**.
- Σε ανομοιογενή batches χρησιμοποιείται το κλασικό inline format (μικρότερο εκεί).

Το app μετρά και τα δύο και διαλέγει **αυτόματα το φθηνότερο**. Ολόκληρη η ονοματολογία (~25.7k
κωδικοί) **δεν** στέλνεται ποτέ — μόνο οι υποψήφιοι που επέλεξε το retrieval (FTS+embeddings).

## Δωρεάν μετάφραση (χωρίς LLM) & English-first

Η κατάταξη TARIC δουλεύει καλύτερα στα **Αγγλικά** (η ΕΕ CN/HS ονοματολογία είναι τυποποιημένη
στα αγγλικά). Πριν την αντιστοίχιση, το ελληνικό query μεταφράζεται σε αγγλικά μέσω **δωρεάν
διαδικτυακού μεταφραστικού** — χωρίς εξάρτηση από LLM (γρήγορο, ντετερμινιστικό):

- **[MyMemory](https://mymemory.translated.net/)** (προεπιλογή, **χωρίς key**): μεταφραστική μνήμη
  με έμφαση σε κείμενα **ΕΕ/ΟΗΕ** — ακριβώς το τελωνειακό λεξιλόγιο. 5000 chars/μέρα (→ 50000 με email).
- **[LibreTranslate](https://libretranslate.com/)** (προαιρετικό, self-hosted/instance).

Αν όλα αποτύχουν → fallback στο LLM. Ελέγχεται από `classify_in_english` στις **Ρυθμίσεις**.

## Custom AI endpoint (local LLM / ollama)

Στις **Ρυθμίσεις → Custom AI endpoint** ορίζεις **δικό σου OpenAI-συμβατό endpoint** (Base URL,
μοντέλο, προαιρετικό key, timeout) και βάζεις `custom` πρώτο στη σειρά providers. Δεν περιορίζεται σε `:free`.

**Παράδειγμα — Ollama (qwen) μέσω Cloudflare tunnel:**
```bash
ollama serve                                      # OpenAI API στο :11434
ollama pull qwen2.5:7b
cloudflared tunnel --url http://localhost:11434   # -> https://xxx.trycloudflare.com
```
Στις Ρυθμίσεις: **Base URL** = `https://xxx.trycloudflare.com/v1` (το `/chat/completions` προστίθεται
αυτόματα), **Μοντέλο** = `qwen2.5:7b`, **Timeout** ~120s (local LLM αργεί στο πρώτο token).

## Web search (γιατί «αργεί» & πώς φέρνουμε σωστά αποτελέσματα)

Η αναζήτηση δεν αργεί επειδή «δεν χρησιμοποιεί browser» — αργεί όταν πέφτει στο **googlesearch-python**
(scraping με sleep + rate-limit). Οι tiers είναι με σειρά ταχύτητας/αξιοπιστίας (`web_search_order`,
default `searxng → duckduckgo → brave → headless → google_cse → googlesearch → openserp`):

1. **[SearXNG](https://github.com/searxng/searxng)** — meta-search (JSON API, χωρίς key). Όρισε
   `searxng_url` (self-host `http://127.0.0.1:8888` **προτείνεται**). Ίδιο endpoint με το mcp-searxng.
2. **DuckDuckGo HTML** — γρήγορο, χωρίς key/όρια.
3. **[Brave Search API](https://brave.com/search/api/)** — επίσημο JSON, ~2000 δωρεάν queries/μήνα (key).
4. **headless browser** — **ΠΡΑΓΜΑΤΙΚΟΣ Chrome μέσω Selenium** που εκτελεί JS· το **ισχυρό fallback**
   που λύνει ό,τι δεν λύνουν τα ελαφριά tiers. `pip install -e ".[headless]"` + εγκατεστημένο Chrome.
   Μηχανή από `headless_engine`: **Brave** (`search.brave.com` — ανεξάρτητος index, anti-bot friendly),
   **Bing** & **DuckDuckGo** δουλεύουν με automation· η **Google** ζητά CAPTCHA (`/sorry`).
   `headless_headed=true` = ορατό παράθυρο· προαιρετικά χρήση πραγματικού προφίλ Chrome
   (cookies/consent) — **κλείσε το Chrome πρώτα**. Δοκιμή: `scripts\search_smoketest.py --engine brave`.
   - **[undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)**
     (`pip install -e ".[anti_bot]"`) χρησιμοποιείται **αυτόματα ΠΡΩΤΑ** (`headless_undetected=true`)
     για παράκαμψη anti-bot (Cloudflare/reCAPTCHA)· αν αποτύχει (π.χ. ασυμβατότητα Chrome version),
     γίνεται **graceful fallback** σε plain Selenium. Σε **Python 3.12+** χρειάζεται και `setuptools`
     (το uc κάνει `import distutils`) — περιλαμβάνεται στο extra.

**Λειτουργικό test αναζήτησης** (headed ή headless, πραγματικός browser):
```bash
.venv\Scripts\python scripts\search_smoketest.py            # headless
.venv\Scripts\python scripts\search_smoketest.py --headed   # ορατό παράθυρο Chrome
```
5. **Google CSE** (100/μέρα δωρεάν, με key+cse_id) · **googlesearch-python** (έσχατο) · **OpenSERP** (docker).

Όλα κάνουν σιωπηλά fallback στο επόμενο. Τα αποτελέσματα τροφοδοτούν το cross-check ταυτότητας (και
χωρίς AI, μέσω corroboration score) + το AI enrichment. Debug: **Ρυθμίσεις → Έλεγχος web search**.

### SearXNG setup (για το μηχάνημα του ollama)

**Με Docker:**
```sh
docker run --rm -d -p 8888:8080 searxng/searxng:latest
```
**Χωρίς Docker:**
```sh
git clone https://github.com/searxng/searxng && cd searxng
python -m venv venv && . venv/bin/activate        # Windows: venv\Scripts\activate
pip install -U pip setuptools wheel pyyaml
pip install --use-pep517 --no-build-isolation -e .
export SEARXNG_SETTINGS_PATH=$PWD/searx/settings.yml   # πρόσθεσε 'json' στο formats
python -m searx.webapp                             # http://127.0.0.1:8888
```
Στο `settings.yml`, το `search.formats` πρέπει να περιλαμβάνει `json`.

**mcp-searxng** (ώστε το τοπικό LLM να κάνει μόνο του αναζητήσεις μέσω MCP):
```json
{ "mcpServers": { "searxng": {
    "command": "npx", "args": ["-y", "mcp-searxng"],
    "env": { "SEARXNG_URL": "http://127.0.0.1:8888" } } } }
```
Πηγή: [ihor-sokoliuk/mcp-searxng](https://github.com/ihor-sokoliuk/mcp-searxng).

## OCR ετικέτας (προαιρετικό)

Όταν οι δομημένες πηγές barcode δεν δίνουν αξιόπιστη ονομασία αλλά υπάρχει **φωτό προϊόντος**,
η εφαρμογή διαβάζει το κείμενο της ετικέτας με OCR ([ocr.space](https://ocr.space/ocrapi), δωρεάν
tier με key) και το τροφοδοτεί στην αναγνώριση/κατάταξη. Key στις **Ρυθμίσεις → Μετάφραση & OCR**.

## Εκτέλεση (dev)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[gui]"
python -m barcodetaric.gui
```

CLI (χωρίς GUI):

```bash
python -m barcodetaric.cli import-taric              # φόρτωση δείγματος ΕΕ ονοματολογίας
python -m barcodetaric.cli import-taric path/to.xlsx # ή επίσημο αρχείο CN
python -m barcodetaric.cli resolve "coffee beans"    # δοκιμή αντιστοίχισης
python -m barcodetaric.cli train                     # εκπαίδευση τοπικού ML
```

## Local installer (Windows, per-user, χωρίς admin)

```powershell
powershell -ExecutionPolicy Bypass -File installer\build.ps1
```

Παράγει `dist\installer\BarcodeTaric-0.1.0-setup.exe` (απαιτεί Inno Setup 6:
`winget install JRSoftware.InnoSetup`).

## Δεδομένα

Όλα (SQLite βάση, μοντέλο, ρυθμίσεις) ζουν ανά-χρήστη στο `%LOCALAPPDATA%\BarcodeTaric`
(ή στο `BARCODETARIC_DATA_DIR`). Δεν χρειάζονται δικαιώματα admin.

## Επίσημη πηγή TARIC

Δεν υπάρχει δωρεάν επίσημο REST API της ΕΕ. Κατεβάζουμε & κάνουμε import τοπικά το
[Combined Nomenclature](https://data.europa.eu/data/datasets/combined-nomenclature-2026)
(ετήσιο, πολύγλωσσο με Ελληνικά). Ο importer δέχεται XML/CSV/XLSX/ZIP από αρχείο ή URL.

## Μηχανική μάθηση (τοπικό, δωρεάν, offline)

Το `ml_classifier.py` μαθαίνει από τα **επιβεβαιωμένα** (✔) είδη και αναλαμβάνει όλο και
περισσότερες αποφάσεις χωρίς κλήση AI. Τρέχουσα προσέγγιση (v2):

- **TF-IDF word (1-2gram) + char_wb (3-5gram)** → LogisticRegression, δύο στάδια (πλήρες TARIC →
  fallback σε HS4). Τα **char n-grams** πιάνουν ελληνική μορφολογία (γάλα/γάλακτος), ορθογραφικά
  λάθη και παραλλαγές μάρκας — που το word-only έχανε.
- **Δομημένη «ανάλυση» προϊόντος** (`analysis`): πίσω από την περιγραφή αποθηκεύεται υλικό/τύπος
  (customs_hint) + κατηγορίες + μάρκα + ποσότητα, στη βάση (στήλες `catalog.analysis`,
  `client_items.analysis`). Χρησιμοποιείται **και** ως feature του ML **και** για ακριβέστερη
  κατάταξη — χωρίς επιπλέον κλήση AI.

### Ποιο είναι το «καλύτερο» μοντέλο; (έρευνα)

- **LLM fine-tuning** (π.χ. Atlas / LLaMA-3.3-70B) δίνει την υψηλότερη ακρίβεια αλλά είναι βαρύ/
  ακριβό — δεν ταιριάζει σε δωρεάν, offline, ελαφρύ desktop.
- **Multilingual sentence-embeddings** (SBERT, π.χ. `paraphrase-multilingual-MiniLM-L12-v2`)
  δίνουν **+7–25%** έναντι TF-IDF+SVM και λύνουν σημασιολογικά κείμενα («Στάμου γάλα αγελάδος»
  → γάλα 0401) — **αλλά** φέρνουν βαριά εξάρτηση (torch, ~εκατοντάδες MB) που χαλάει τον
  ελαφρύ installer. Γι' αυτό μπαίνει ως **μελλοντικό optional extra** με το ΙΔΙΟ interface
  (`get_model().predict(...)`), όχι στο default bundle.

Πηγές έρευνας: [ATLAS (arXiv 2509.18400)](https://arxiv.org/html/2509.18400v1) ·
[HS code AI guide 2025](https://www.xnovainternational.com/post/hs-code-a-practical-guide-to-automatic-classification-with-ai-2025) ·
[TF-IDF vs Sentence Transformers](https://medium.com/@venugopal.adep/comparative-study-of-text-embeddings-tf-idf-vs-sentence-transformer-28627c315f21)

## Εκκρεμή / Μελλοντικά

- **Semantic ML backend (sentence-embeddings)** ως optional extra `.[semantic]` — το πραγματικό
  fix για ασαφείς ελληνικές περιγραφές (π.χ. «Στάμου γάλα αγελάδος»). Interface έτοιμο· δεν
  υλοποιήθηκε ακόμη για να μη βαρύνει ο installer.
- **Πλουσιότερη AI «ανάλυση»**: τώρα η `analysis` συντίθεται από hint+κατηγορίες+μάρκα+ποσότητα
  (χωρίς επιπλέον κλήση, για ταχύτητα). Μια αναλυτική AI ανάλυση σύστασης/υλικών θα βοηθούσε
  ακόμη περισσότερο αλλά προσθέτει κόστος/χρόνο — αφέθηκε ως επιλογή.
- **Speed:** το resolve κάνει 2 AI κλήσεις (confirm_product + rank_taric) + web· όταν ωριμάσει το
  ML tier, οι AI κλήσεις πέφτουν αυτόματα.

## Tests

```bash
pip install -e ".[gui]" pytest
pytest
```
