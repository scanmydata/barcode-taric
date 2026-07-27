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
- **Τοπικό μοντέλο ML** (scikit-learn) που μαθαίνει από τα **επιβεβαιωμένα** είδη· όσο μεγαλώνει το dataset,
  αναλαμβάνει όλο και περισσότερες αποφάσεις **χωρίς κλήση AI**.
- **Export** κωδικολογίου πελάτη με τους σωστούς TARIC σε Excel/CSV.

## Πώς «ασφαλίζεται» η περιγραφή πριν την κατάταξη

Για να μη γίνονται λάθη τύπου «X water → toilet water (άρωμα)», η ροή διασταυρώνει
πηγές πριν κατατάξει:

1. **Δομημένες πηγές barcode** (OpenFoodFacts/UPC/…) δίνουν υποψήφια ονομασία —
   με φίλτρο που απορρίπτει «σκουπίδια» (τίτλους των ίδιων των sites αναζήτησης).
2. **Παράλληλη αναζήτηση web** για το barcode **και** για την ονομασία (cross-check).
3. Ένα **AI βήμα** «κλειδώνει» σύντομη **ονομασία EL/EN** (μόνο *τι είναι*, όχι
   αναλυτική περιγραφή), αν είναι **προϊόν ή υπηρεσία**, και ένα εσωτερικό
   `customs_hint` (π.χ. *natural mineral water, bottled*) που ξεχωρίζει το νερό
   (2201) από το άρωμα (3303).
4. **Υπηρεσίες/άυλα δεν λαμβάνουν TARIC.** Τα προϊόντα κατατάσσονται με το hint.
5. **Δικλείδα χωρίς AI:** όταν η πηγή είναι τρόφιμο (OpenFoodFacts), η κατάταξη
   προτιμά τα κεφάλαια τροφίμων/ποτών (01–24), ώστε το «water» να μη γίνει άρωμα
   ακόμη κι όταν το AI δεν είναι διαθέσιμο.

## Δωρεάν AI

<<<<<<< HEAD
Χρησιμοποιεί δωρεάν providers με σειρά (`ai_provider_order`): **OpenRouter** (`:free` μοντέλα,
χρειάζεται API key) → **custom** (προαιρετικό δικό σου endpoint) → **DuckDuckGo** → **Pollinations**.
Το **Groq** υπάρχει ως μελλοντική (απενεργοποιημένη) επιλογή. Τα κλειδιά μπαίνουν από τη σελίδα **Ρυθμίσεις**.

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
=======
Συνιστάται το **OpenRouter** με δωρεάν (`:free`) μοντέλο — χρειάζεται μόνο ένα
δωρεάν API key. Τα no-key providers (**Pollinations**/**DuckDuckGo**) πλέον
χρεώνουν/περιορίζονται (HTTP 402/429) και μένουν μόνο ως έσχατο fallback. Υπάρχει
και **Groq** ως εναλλακτική (προαιρετικό key). Σειρά:
`openrouter → groq → duckduckgo → pollinations`. Τα κλειδιά μπαίνουν από τη σελίδα
**Ρυθμίσεις**.

## Πραγματικά Google results (OpenSERP)

Το απλό scraping της Google μπλοκάρεται. Για αξιόπιστα, **χωρίς API key**,
αποτελέσματα η εφαρμογή υποστηρίζει το [OpenSERP](https://github.com/karust/openserp)
— έναν τοπικό server που οδηγεί headless browser. Εκκίνηση:

```sh
docker run --rm -p 127.0.0.1:7000:7000 karust/openserp:latest serve -a 0.0.0.0 -p 7000
```

Αν τρέχει (προεπιλογή `http://127.0.0.1:7000`, ρυθμίζεται στις **Ρυθμίσεις**),
προτιμάται πρώτο απ' όλα τα web tiers και τροφοδοτεί το cross-check + AI. Αν δεν
τρέχει, γίνεται σιωπηλά fallback σε googlesearch/CSE/DuckDuckGo.
>>>>>>> f91a0af2a8db04d710b4d264026c0311eea1ae33

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

## Tests

```bash
pip install -e ".[gui]" pytest
pytest
```
