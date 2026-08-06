# AGENT_MEMORY — accumulated project knowledge (for future agents/sessions)

This file mirrors the assistant's persistent memory about **BarcodeTaric** so the knowledge
travels with the repo. It complements `CLAUDE.md` (the how-it-works guide) with the **why**
and the hard-won lessons. Keep it updated when a decision or gotcha proves important.

## Who / what
- **User:** Greek customs & accounting professional. Non-obvious requirements often come from
  real customs workflow, not the code. UI/labels are Greek.
- **App:** local PySide6 desktop app — πελατολόγιο + barcode→περιγραφή→TARIC matching + Excel
  export, fully free (free AI + local ML) and offline after importing the EU CN nomenclature.

## Core directive — classification is DESCRIPTION-based, AI is the arbiter
The user was explicit: **always classify TARIC from the product description, by the AI.**
Flow: extract description from the barcode (esp. OpenFoodFacts) → cross-check with web search
results (help the AI understand the product) → **AI** picks the code. «παμε παντα βαση description».
- No-AI matching (FTS + semantic) tops out ~60% correct HS4 on ambiguous cases
  (e.g. coffee beans `0901` vs instant-coffee extract `2101`). Don't try to close that gap by
  tuning FTS — improve description quality + the AI prompt. Keep `match(..., use_ai=True)` as the
  accurate path; bulk fast (no-AI) results are provisional/review only.

## Scale — every client has 4,000–10,000 codes
Every bulk path must scale. **Per-call SQLite overhead is the #1 bottleneck:** `db.connect()`
opens a new connection + PRAGMAs per call, so any `connect()`-per-row function in a hot loop
turns seconds into minutes.
- Use the bulk repo functions (one transaction): `bulk_upsert_client_items`,
  `bulk_update_client_items`, `delete_client_items`, `bulk_upsert_catalog`, `bulk_insert_taric`.
- `taric_match._rowcount()` caches the row count (was reopening a connection per token weight).
- Measured: Excel insert 5000 rows 42s→0.06s (~700x); match 0.8/s→29/s (~35x); 10k ≈ 5.7 min
  FTS / ~10 min semantic; Excel read 5000/0.25s, export/0.76s.

## The "TARIC import freezes the whole app" bug
Root cause was **no `busy_timeout`**: the long 25k-row `bulk_insert_taric` write lock stalled
every UI-thread DB read. Fixed with `PRAGMA busy_timeout=30000` + `sqlite3.connect(timeout=30)`
in `db.connect()`. Residual sluggishness during xlsx **parse** is GIL-bound (a QThread does not
free the GIL); a `BusyOverlay` communicates progress. If a truly freeze-free heavy import is
needed, run it in a **subprocess** (not just a QThread).

## UI patterns & gotchas
- **Checkbox tables:** col 0 is a checkable `QTableWidgetItem`; the row **id lives on col-0 via
  `Qt.UserRole+1`** (survives sorting); a `_loading` flag guards `itemChanged` during `reload()`;
  "Επιλογή όλων" + `_checked_ids()`/`_target_ids()` drive bulk actions. Used in `codebook_page`
  and `catalog_page`.
- **Qt checkbox indicators are invisible under a global stylesheet unless styled.** `theme.py`
  now styles `QCheckBox/QTableView::indicator` and generates an SVG checkmark
  (`theme._check_icon`, colored with `accent_txt`, written to data-dir). This was the reported
  "visual issue in light & dark".
- **Merges silently drop lines.** A conflict resolution once dropped `self._value = QLabel(value)`
  in `StatTile.__init__`, crashing the Clients page. After any merge, smoke-test each page
  offscreen (`QT_QPA_PLATFORM=offscreen`). Offscreen renders Greek as tofu (□) — a missing font,
  NOT a bug; colors/layout/QSS are still valid to inspect.
- **`widgets.BusyOverlay(parent)`** — semi-transparent overlay + indeterminate `QProgressBar`;
  `.start(msg)/.set_message/.stop()`; follows parent via eventFilter. Wrap long workers.

## Import / export with extra columns + backup
- **Import mapping dialog** (`gui/import_dialog.py`): `reader.preview_columns()` auto-detects
  barcode/desc/taric and lets the user keep EXTRA columns (internal product codes, details…).
  `reader.read_with_mapping()` returns `ImportedRow.extra` (dict), stored as JSON in the new
  `client_items.extra` column.
- **Export** (`excel/exporter.py`, `include_extra=True`) re-emits the kept extra columns; the
  export dialog (`_ExportDialog`) explains which columns go out and toggles extras.
- **Auto-backup** `db.backup_db(tag)` (SQLite online-backup API → `data-dir/backups/`, keeps the
  10 most recent) runs before every import and export; it must never break the flow.

## Dev environment
- No `.venv` in repo. Default `py` is Python 3.14; PySide6/scikit-learn want **3.12**
  (uv-managed 3.12.6 on this machine). `PYTHONUTF8=1 .venv/Scripts/python -m pytest` → **46 tests**,
  all offline. `QT_QPA_PLATFORM=offscreen` for headless GUI smoke tests. `conftest.py` neutralizes
  network so the suite doesn't hang on real AI/Chrome.
