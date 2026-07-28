# BarcodeTaric

Τοπικό desktop app (PySide6) για **πελατολόγιο** και αντιστοίχιση **barcode → περιγραφή → TARIC**.

## Τι κάνει

- **Πελατολόγιο με CRUD** — διαχείριση πελατών, ανά πελάτη δικό του κωδικολόγιο.
- **Import κωδικολογίου από Excel/CSV** (auto-detect στηλών barcode/περιγραφή) ή **add-by-barcode**
  με αναζήτηση σε πολλαπλές πηγές + πραγματικά **Google results** (googlesearch → Google CSE → DuckDuckGo)
  και AI web-inference όταν δεν βρίσκεται περιγραφή.
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

Συνιστάται το **OpenRouter** με δωρεάν (`:free`) μοντέλο — χρειάζεται μόνο ένα
δωρεάν API key. Τα no-key providers (**Pollinations**/**DuckDuckGo**) πλέον
χρεώνουν/περιορίζονται (HTTP 402/429) και μένουν μόνο ως έσχατο fallback. Υπάρχει
και **Groq** ως εναλλακτική (προαιρετικό key). Σειρά:
`openrouter → groq → duckduckgo → pollinations`. Τα κλειδιά μπαίνουν από τη σελίδα
**Ρυθμίσεις**.

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
