# open-webSearch — τοπική δωρεάν αναζήτηση (χωρίς API keys)

[open-webSearch](https://github.com/Aas-ee/open-webSearch) είναι ένας **multi-engine** web
search server (Bing, DuckDuckGo, Brave, Startpage, Baidu, Sogou…) που δουλεύει με **scraping,
χωρίς κανένα API key**. Τρέχει τοπικά και εκθέτει ένα απλό HTTP `/search` endpoint — ιδανικό
για το **μηχάνημα που τρέχει το τοπικό LLM (ollama)**, ώστε το BarcodeTaric να παίρνει
αποτελέσματα αναζήτησης τοπικά και αξιόπιστα.

Το BarcodeTaric το υποστηρίζει **out of the box** ως web-search tier `open_websearch`
(καμία νέα Python εξάρτηση — μόνο `urllib`, όπως το SearXNG). Απλώς σήκωσε τον server και
δώσε το URL στις Ρυθμίσεις.

## 1) Σήκωσε τον server (διάλεξε έναν τρόπο)

**NPX (γρήγορο, θέλει Node.js):**
```bash
ENABLE_CORS=true DEFAULT_SEARCH_ENGINE=duckduckgo npx open-websearch@latest
```

**Docker (run):**
```bash
docker run -d --name web-search -p 3000:3000 \
  -e ENABLE_CORS=true -e CORS_ORIGIN=* \
  ghcr.io/aas-ee/open-web-search:latest
```

**Docker Compose:** δες `docker-compose.open-websearch.yml` σε αυτόν τον φάκελο:
```bash
docker compose -f docs/docker-compose.open-websearch.yml up -d
```

Ο server ακούει στη **θύρα 3000** (`http://localhost:3000`). Χρήσιμα env vars:
`PORT`, `DEFAULT_SEARCH_ENGINE`, `MODE` (`http`/`stdio`/`both`), `SEARCH_MODE`
(`request`/`auto`/`playwright`), `USE_PROXY`/`PROXY_URL`, `ENABLE_CORS`.

## 2) Δοκίμασε ότι δουλεύει
```bash
curl -s -X POST http://localhost:3000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"nescafe classic instant coffee","limit":5}'
```
Πρέπει να γυρίσει JSON array με `{title,url,description,source,engine}`.

## 3) Ρύθμισε το BarcodeTaric
Στις **Ρυθμίσεις → Web search** (ή στο `settings.json` του data-dir):
- `open_websearch_url` = `http://localhost:3000` (ή το URL του τοπικού μηχανήματος/tunnel)
- (προαιρετικά) `open_websearch_engines` = π.χ. `["bing","duckduckgo","brave"]`
- (προαιρετικά) `open_websearch_timeout` = `15`

Το tier `open_websearch` είναι ήδη **δεύτερο στη σειρά** (μετά το SearXNG) στο
`web_search_order`, οπότε μόλις οριστεί το URL χρησιμοποιείται αυτόματα.

> **Σημ.:** Αν το τρέχεις σε ΑΛΛΟ μηχάνημα (αυτό του local LLM), βάλε εκεί `ENABLE_CORS=true`
> και δώσε στο `open_websearch_url` το προσβάσιμο URL (LAN IP ή Cloudflare tunnel), όπως ακριβώς
> κάνεις και με το custom AI endpoint του ollama.
