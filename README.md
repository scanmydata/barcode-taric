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

<<<<<<< HEAD
## Δωρεάν μετάφραση (χωρίς LLM) & English-first

Η κατάταξη TARIC δουλεύει καλύτερα στα **Αγγλικά** (η ΕΕ CN/HS ονοματολογία είναι
τυποποιημένη στα αγγλικά). Γι' αυτό, πριν την αντιστοίχιση, το ελληνικό query
μεταφράζεται σε αγγλικά μέσω **δωρεάν διαδικτυακού μεταφραστικού** — **χωρίς** εξάρτηση
από LLM (γρήγορο & ντετερμινιστικό):

- **[MyMemory](https://mymemory.translated.net/)** (προεπιλογή, **χωρίς key**): τεράστια
  μεταφραστική μνήμη με έμφαση σε κείμενα **ΕΕ/ΟΗΕ** — ακριβώς το τελωνειακό/εμπορικό
  λεξιλόγιο. Όριο 5000 chars/μέρα (→ 50000 με προαιρετικό email στις **Ρυθμίσεις**).
- **[LibreTranslate](https://libretranslate.com/)** (προαιρετικό, self-hosted/instance).

Αν όλα αποτύχουν, γίνεται fallback στο LLM. Η επιλογή «Κατάταξη με βασική γλώσσα τα
Αγγλικά» ελέγχεται από τις **Ρυθμίσεις** (`classify_in_english`).

## Πραγματικά Google results (γιατί «αργεί» η αναζήτηση)

Η αναζήτηση δεν αργεί επειδή «δεν χρησιμοποιεί browser» — αργεί όταν πέφτει στο
**googlesearch-python**, που κάνει scraping με **sleep μεταξύ requests** και
rate-limiting. Γι' αυτό οι tiers είναι πλέον με σειρά ταχύτητας/αξιοπιστίας:

1. **[OpenSERP](https://github.com/karust/openserp)** — τοπικός server με **headless browser**,
   πραγματικά Google αποτελέσματα **χωρίς API key**. Εκκίνηση:
   ```sh
   docker run --rm -p 127.0.0.1:7000:7000 karust/openserp:latest serve -a 0.0.0.0 -p 7000
   ```
   (προεπιλογή `http://127.0.0.1:7000`, ρυθμίζεται στις **Ρυθμίσεις**).
2. **[Brave Search API](https://brave.com/search/api/)** — επίσημο, **γρήγορο**, δομημένο JSON,
   ~**2000 δωρεάν queries/μήνα** με key.
3. **Google CSE** (100/μέρα δωρεάν, με key+cse_id).
4. **DuckDuckGo HTML** (χωρίς key/όρια).
5. **googlesearch-python** — έσχατο, αργό/rate-limited.

Όλα τα tiers κάνουν σιωπηλά fallback στο επόμενο αν αποτύχουν. Τα αποτελέσματα
τροφοδοτούν το cross-check ταυτότητας (και χωρίς AI, μέσω corroboration score) + το AI.

## Τοπικό LLM (ollama) + SearXNG

Για δικό σου **self-hosted LLM** (π.χ. ollama μέσω cloudflare tunnel), πρόσθεσε τον
`custom` provider στις **Ρυθμίσεις → AI**: βάλε το **Custom endpoint URL** (base ή πλήρες
`/v1/chat/completions`), model και προαιρετικό key, και φέρε το `custom` πρώτο στη
**Σειρά providers**. Είναι OpenAI-compatible, οπότε δουλεύει με το `/v1` του ollama.

Για **πολλαπλές αναζητήσεις χωρίς rate-limit**, στήσε **SearXNG** (μετα-μηχανή) στο ίδιο
μηχάνημα και βάλε το URL στις **Ρυθμίσεις → Web search → SearXNG URL**. Πρέπει να έχει
ενεργό το JSON format (`search.formats: [html, json]` στο `settings.yml`).

**SearXNG με Docker:**
```sh
docker run --rm -d -p 8080:8080 -v ./searxng:/etc/searxng searxng/searxng:latest
```

**SearXNG χωρίς Docker** (π.χ. στο μηχάνημα του ollama):
```sh
git clone https://github.com/searxng/searxng && cd searxng
python -m venv venv && . venv/bin/activate        # Windows: venv\Scripts\activate
pip install -U pip setuptools wheel pyyaml
pip install --use-pep517 --no-build-isolation -e .
export SEARXNG_SETTINGS_PATH=$PWD/searx/settings.yml   # πρόσθεσε 'json' στο formats
python -m searx.webapp                             # http://127.0.0.1:8888
```

**mcp-searxng** (ώστε το τοπικό LLM να κάνει μόνο του αναζητήσεις μέσω MCP):
```json
{ "mcpServers": { "searxng": {
    "command": "npx", "args": ["-y", "mcp-searxng"],
    "env": { "SEARXNG_URL": "http://127.0.0.1:8888" } } } }
```
Πηγή: [ihor-sokoliuk/mcp-searxng](https://github.com/ihor-sokoliuk/mcp-searxng).

## OCR ετικέτας (προαιρετικό)

Όταν οι δομημένες πηγές barcode δεν δίνουν αξιόπιστη ονομασία αλλά υπάρχει **φωτό
προϊόντος** (π.χ. από OpenFoodFacts), η εφαρμογή μπορεί να διαβάσει το κείμενο της
ετικέτας με OCR ([ocr.space](https://ocr.space/ocrapi), δωρεάν tier με key) και να το
τροφοδοτήσει στην αναγνώριση/κατάταξη. Το key μπαίνει στις **Ρυθμίσεις → Μετάφραση & OCR**.
Χωρίς key, το βήμα παρακάμπτεται σιωπηλά.
=======
> ⚠️ **Το free-model landscape του OpenRouter αλλάζει συχνά** — μοντέλα αποσύρονται και το API
> επιστρέφει `404`. Το app το χειρίζεται **αυτόματα**: αν το ρυθμισμένο μοντέλο αποτύχει (404),
> δοκιμάζει εναλλακτικά (`openai/gpt-oss-20b:free` → `openrouter/free`) και «θυμάται» αυτό που
> δουλεύει για τη session. Στις **Ρυθμίσεις** υπάρχει **«Έξυπνη επιλογή»** που δοκιμάζει τα κορυφαία
> δωρεάν μοντέλα και επιλέγει ένα που απαντά, καθώς και **«Λίστα μοντέλων»** (φιλτραρισμένα chat
> μοντέλα, χωρίς audio/image/embeddings). Default: `openai/gpt-oss-20b:free`.

### Custom AI endpoint (local LLM / on-prem)

Στις **Ρυθμίσεις → Custom AI endpoint** ορίζεις **δικό σου OpenAI-συμβατό endpoint** (Base URL,
μοντέλο, προαιρετικό key, timeout). Βάλε `custom` στη σειρά providers. Δεν περιορίζεται σε `:free`.

**Παράδειγμα — Ollama (qwen) μέσω Cloudflare tunnel:**

```bash
ollama serve                                   # τοπικό Ollama (OpenAI API στο :11434)
ollama pull qwen2.5:7b
cloudflared tunnel --url http://localhost:11434   # δίνει https://xxx.trycloudflare.com
```

Στις Ρυθμίσεις: **Base URL** = `https://xxx.trycloudflare.com/v1` (το `/chat/completions`
προστίθεται αυτόματα), **Μοντέλο** = `qwen2.5:7b`, **API key** κενό, **Timeout** ~120s (local LLM
αργεί στο πρώτο token).

## Web search (SearXNG + headless Chrome + fallbacks)

Τα web results έρχονται σε επίπεδα (`web_search_order`, default:
`searxng → duckduckgo → headless → googlesearch → google_cse`):

1. **SearXNG** — meta-search ([searxng/searxng](https://github.com/searxng/searxng)) με JSON API.
   Όρισε `searxng_url` στις Ρυθμίσεις (self-host `http://127.0.0.1:8888` **προτείνεται** — πολλά public
   instances κλείνουν το `format=json`). Ίδιο endpoint με το [mcp-searxng](https://github.com/ihor-sokoliuk/mcp-searxng).
2. **DuckDuckGo HTML** — γρήγορο & αξιόπιστο fallback χωρίς key/όρια.
3. **headless Chrome (Google)** — πραγματικό Chrome μέσω **Selenium** που εκτελεί JS και διαβάζει τα
   οργανικά αποτελέσματα της Google (παρακάμπτει το block του απλού scraping). Θέλει
   `pip install -e ".[headless]"` + εγκατεστημένο Chrome. ⚠️ Η Google **rate-limit-άρει** με CAPTCHA
   (`/sorry`) σε πολλά διαδοχικά queries — τότε το tier επιστρέφει κενό και πέφτει σε DuckDuckGo.
   Για Google-first, βάλε `headless` πρώτο στη «Σειρά web tiers»· `headless_headed=true` = ορατό
   παράθυρο (λιγότερο ανιχνεύσιμο ως bot).
4. **googlesearch-python** — απλό scraping (η Google συχνά το μπλοκάρει → κενά αποτελέσματα).
5. **Google CSE JSON API** — αν έχεις `google_cse_api_key` + `google_cse_id` (100 queries/μέρα δωρεάν).

Το web search χρησιμοποιείται και **στη λήψη περιγραφής από barcode**: αφού μια δομημένη πηγή
(OpenFoodFacts κ.λπ.) δώσει όνομα, γίνεται αναζήτηση στο web **με το όνομα** και τα snippets
τροφοδοτούν το AI enrichment για ακριβέστερη περιγραφή → καλύτερο TARIC.

Debug: **Ρυθμίσεις → Debugger → Έλεγχος web search** δείχνει ποιο tier απαντά.

### Self-host SearXNG (προαιρετικό, με Docker)

```bash
docker run -d --name searxng -p 8888:8080 \
  -e "SEARXNG_BASE_URL=http://localhost:8888/" searxng/searxng
```

Στο `settings.yml` του instance βεβαιώσου ότι το `search.formats` περιλαμβάνει `json`.
>>>>>>> b69f1c064e06f3062b3591fa58b396eb91ebe117

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
