"""CRUD repositories πάνω από το SQLite schema."""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from typing import Any, Optional

from .db import connect
from .engine.http_util import stem_token
from .models import CatalogItem, Client, ClientItem, TaricRow


# ---------------------------------------------------------------- helpers ----

def _strip_accents(text: str) -> str:
    lowered = text.lower()
    return "".join(c for c in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(c))


def _fold(*parts: str) -> str:
    """Folded κείμενο για το FTS index: πεζά, χωρίς τόνους, μόνο γράμματα/ψηφία."""
    joined = " ".join(p for p in parts if p)
    stripped = _strip_accents(joined)
    return re.sub(r"[^0-9a-zα-ω]+", " ", stripped).strip()


def _fts_upsert(conn: sqlite3.Connection, fts: str, rowid: int, text: str) -> None:
    conn.execute(f"DELETE FROM {fts} WHERE rowid=?", (rowid,))
    conn.execute(f"INSERT INTO {fts}(rowid, text) VALUES (?, ?)", (rowid, text))


def _fts_query(text: str) -> str:
    """Μετατρέπει ελεύθερο κείμενο σε ασφαλές FTS5 MATCH.

    Κάθε token γίνεται stem + prefix (stem*) ώστε ενικός/πληθυντικός και κλίσεις
    (water/waters, νερό/νερά) να ταιριάζουν, και ενώνονται με OR.
    """
    stripped = _strip_accents(text)
    tokens = [t for t in re.split(r"[^0-9a-zα-ω]+", stripped) if len(t) > 1]
    stems = {stem_token(t) for t in tokens}
    stems = {s for s in stems if len(s) > 1}
    return " OR ".join(f"{s}*" for s in stems)


def _touch(cursor: sqlite3.Cursor, table: str, row_id: int) -> None:
    cursor.execute(f"UPDATE {table} SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (row_id,))


# ---------------------------------------------------------------- clients ----

def create_client(client: Client) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO clients (name, vat, email, phone, address, notes) VALUES (?,?,?,?,?,?)",
            (client.name, client.vat, client.email, client.phone, client.address, client.notes),
        )
        return int(cur.lastrowid)


def update_client(client: Client) -> bool:
    with connect() as conn:
        cur = conn.execute(
            """UPDATE clients SET name=?, vat=?, email=?, phone=?, address=?, notes=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (client.name, client.vat, client.email, client.phone,
             client.address, client.notes, client.id),
        )
        return cur.rowcount > 0


def delete_client(client_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
        return cur.rowcount > 0


def get_client(client_id: int) -> Optional[Client]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        return _row_to_client(row) if row else None


def list_clients(search: str = "") -> list[Client]:
    with connect() as conn:
        if search.strip():
            like = f"%{search.strip()}%"
            rows = conn.execute(
                "SELECT * FROM clients WHERE name LIKE ? OR vat LIKE ? ORDER BY name",
                (like, like),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
        return [_row_to_client(r) for r in rows]


def client_stats(client_id: int) -> dict[str, int]:
    with connect() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN taric_code IS NOT NULL AND taric_code != '' THEN 1 ELSE 0 END) AS matched,
                      SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) AS verified
               FROM client_items WHERE client_id = ?""",
            (client_id,),
        ).fetchone()
        total = row["total"] or 0
        matched = row["matched"] or 0
        verified = row["verified"] or 0
        return {"total": total, "matched": matched,
                "unmatched": total - matched, "verified": verified}


def _row_to_client(row: sqlite3.Row) -> Client:
    return Client(
        id=row["id"], name=row["name"], vat=row["vat"] or "", email=row["email"] or "",
        phone=row["phone"] or "", address=row["address"] or "", notes=row["notes"] or "",
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


# ---------------------------------------------------------------- catalog ----

def upsert_catalog(item: CatalogItem) -> int:
    """Εισαγωγή/ενημέρωση εγγραφής στην κεντρική βάση γνώσης (κλειδί: barcode)."""
    with connect() as conn:
        existing = None
        if item.barcode:
            existing = conn.execute(
                "SELECT id FROM catalog WHERE barcode=?", (item.barcode,)
            ).fetchone()
        if existing:
            cid = int(existing["id"])
            conn.execute(
                """UPDATE catalog SET description_el=?, description_en=?, taric_code=?, hs4=?,
                   taric_description=?, confidence=?, ai_rationale=?, taric_source=?, verified=?,
                   source=?, brand=?, quantity=?, categories=?, analysis=?,
                   updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (item.description_el, item.description_en, item.taric_code, item.hs4,
                 item.taric_description, item.confidence, item.ai_rationale, item.taric_source,
                 item.verified, item.source, item.brand, item.quantity, item.categories,
                 item.analysis, cid),
            )
            _fts_upsert(conn, "catalog_fts", cid,
                        _fold(item.description_el, item.description_en, item.barcode, item.categories))
            return cid
        cur = conn.execute(
            """INSERT INTO catalog (barcode, description_el, description_en, taric_code, hs4,
               taric_description, confidence, ai_rationale, taric_source, verified, source,
               brand, quantity, categories, analysis)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (item.barcode, item.description_el, item.description_en, item.taric_code, item.hs4,
             item.taric_description, item.confidence, item.ai_rationale, item.taric_source,
             item.verified, item.source, item.brand, item.quantity, item.categories,
             item.analysis),
        )
        cid = int(cur.lastrowid)
        _fts_upsert(conn, "catalog_fts", cid,
                    _fold(item.description_el, item.description_en, item.barcode, item.categories))
        return cid


def get_catalog_by_barcode(barcode: str) -> Optional[CatalogItem]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM catalog WHERE barcode=?", (barcode,)).fetchone()
        return _row_to_catalog(row) if row else None


def search_catalog(text: str, limit: int = 50) -> list[CatalogItem]:
    with connect() as conn:
        q = _fts_query(text)
        if q:
            try:
                rows = conn.execute(
                    """SELECT c.* FROM catalog c JOIN catalog_fts f ON c.id=f.rowid
                       WHERE catalog_fts MATCH ? ORDER BY rank LIMIT ?""",
                    (q, limit),
                ).fetchall()
                if rows:
                    return [_row_to_catalog(r) for r in rows]
            except sqlite3.OperationalError:
                pass
        like = f"%{text.strip()}%"
        rows = conn.execute(
            """SELECT * FROM catalog WHERE description_el LIKE ? OR description_en LIKE ?
               OR barcode LIKE ? LIMIT ?""",
            (like, like, like, limit),
        ).fetchall()
        return [_row_to_catalog(r) for r in rows]


def list_catalog(limit: int = 500) -> list[CatalogItem]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM catalog ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_catalog(r) for r in rows]


def update_catalog_item(item: CatalogItem) -> bool:
    with connect() as conn:
        cur = conn.execute(
            """UPDATE catalog SET barcode=?, description_el=?, description_en=?, taric_code=?,
               hs4=?, taric_description=?, confidence=?, ai_rationale=?, taric_source=?,
               verified=?, source=?, brand=?, quantity=?, categories=?, analysis=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (item.barcode, item.description_el, item.description_en, item.taric_code, item.hs4,
             item.taric_description, item.confidence, item.ai_rationale, item.taric_source,
             item.verified, item.source, item.brand, item.quantity, item.categories,
             item.analysis, item.id),
        )
        if cur.rowcount > 0:
            _fts_upsert(conn, "catalog_fts", int(item.id),
                        _fold(item.description_el, item.description_en, item.barcode, item.categories))
        return cur.rowcount > 0


def delete_catalog_item(item_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM catalog WHERE id=?", (item_id,))
        conn.execute("DELETE FROM catalog_fts WHERE rowid=?", (item_id,))
        return cur.rowcount > 0


def _row_to_catalog(row: sqlite3.Row) -> CatalogItem:
    keys = row.keys()
    return CatalogItem(
        id=row["id"], barcode=row["barcode"] or "", description_el=row["description_el"] or "",
        description_en=row["description_en"] or "", taric_code=row["taric_code"] or "",
        hs4=row["hs4"] or "", taric_description=row["taric_description"] or "",
        confidence=row["confidence"] or 0.0, ai_rationale=row["ai_rationale"] or "",
        taric_source=row["taric_source"] or "", verified=row["verified"] or 0,
        source=row["source"] or "",
        brand=(row["brand"] if "brand" in keys else "") or "",
        quantity=(row["quantity"] if "quantity" in keys else "") or "",
        categories=(row["categories"] if "categories" in keys else "") or "",
        analysis=(row["analysis"] if "analysis" in keys else "") or "",
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


# ------------------------------------------------------------ client_items ----

def upsert_client_item(item: ClientItem) -> int:
    """Εισαγωγή/ενημέρωση γραμμής κωδικολογίου πελάτη (κλειδί: client_id+barcode)."""
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM client_items WHERE client_id=? AND barcode=?",
            (item.client_id, item.barcode),
        ).fetchone() if item.barcode else None
        if existing:
            iid = int(existing["id"])
            conn.execute(
                """UPDATE client_items SET description_el=?, description_en=?, taric_code=?, hs4=?,
                   taric_description=?, confidence=?, ai_rationale=?, taric_source=?, verified=?,
                   source=?, brand=?, quantity=?, categories=?, analysis=?, catalog_id=?,
                   updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (item.description_el, item.description_en, item.taric_code, item.hs4,
                 item.taric_description, item.confidence, item.ai_rationale, item.taric_source,
                 item.verified, item.source, item.brand, item.quantity, item.categories,
                 item.analysis, item.catalog_id, iid),
            )
            return iid
        cur = conn.execute(
            """INSERT INTO client_items (client_id, barcode, description_el, description_en,
               taric_code, hs4, taric_description, confidence, ai_rationale, taric_source,
               verified, source, brand, quantity, categories, analysis, catalog_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (item.client_id, item.barcode, item.description_el, item.description_en,
             item.taric_code, item.hs4, item.taric_description, item.confidence,
             item.ai_rationale, item.taric_source, item.verified, item.source,
             item.brand, item.quantity, item.categories, item.analysis, item.catalog_id),
        )
        return int(cur.lastrowid)


def get_client_item(item_id: int) -> Optional[ClientItem]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM client_items WHERE id=?", (item_id,)).fetchone()
        return _row_to_client_item(row) if row else None


def list_client_items(client_id: int, only_unmatched: bool = False) -> list[ClientItem]:
    with connect() as conn:
        sql = "SELECT * FROM client_items WHERE client_id=?"
        if only_unmatched:
            sql += " AND (taric_code IS NULL OR taric_code='')"
        sql += " ORDER BY id"
        rows = conn.execute(sql, (client_id,)).fetchall()
        return [_row_to_client_item(r) for r in rows]


def update_client_item(item: ClientItem) -> bool:
    with connect() as conn:
        cur = conn.execute(
            """UPDATE client_items SET barcode=?, description_el=?, description_en=?, taric_code=?,
               hs4=?, taric_description=?, confidence=?, ai_rationale=?, taric_source=?,
               verified=?, source=?, brand=?, quantity=?, categories=?, analysis=?, catalog_id=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (item.barcode, item.description_el, item.description_en, item.taric_code, item.hs4,
             item.taric_description, item.confidence, item.ai_rationale, item.taric_source,
             item.verified, item.source, item.brand, item.quantity, item.categories,
             item.analysis, item.catalog_id, item.id),
        )
        return cur.rowcount > 0


def delete_client_item(item_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM client_items WHERE id=?", (item_id,))
        return cur.rowcount > 0


def set_item_verified(item_id: int, verified: int = 1) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE client_items SET verified=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (verified, item_id),
        )


def _row_to_client_item(row: sqlite3.Row) -> ClientItem:
    keys = row.keys()
    return ClientItem(
        id=row["id"], client_id=row["client_id"], barcode=row["barcode"] or "",
        description_el=row["description_el"] or "", description_en=row["description_en"] or "",
        taric_code=row["taric_code"] or "", hs4=row["hs4"] or "",
        taric_description=row["taric_description"] or "", confidence=row["confidence"] or 0.0,
        ai_rationale=row["ai_rationale"] or "", taric_source=row["taric_source"] or "",
        verified=row["verified"] or 0, source=row["source"] or "",
        brand=(row["brand"] if "brand" in keys else "") or "",
        quantity=(row["quantity"] if "quantity" in keys else "") or "",
        categories=(row["categories"] if "categories" in keys else "") or "",
        analysis=(row["analysis"] if "analysis" in keys else "") or "",
        catalog_id=row["catalog_id"], created_at=row["created_at"], updated_at=row["updated_at"],
    )


# ------------------------------------------------------- training / ML data ----

def verified_training_rows() -> list[dict[str, Any]]:
    """Επιστρέφει τα επιβεβαιωμένα ζεύγη (περιγραφή -> TARIC) για εκπαίδευση ML.

    Αντλεί από client_items ΚΑΙ catalog (verified=1) με έγκυρο taric_code.
    """
    with connect() as conn:
        rows = conn.execute(
            """SELECT description_el, description_en, barcode, brand, quantity, categories,
                      analysis, taric_code, hs4
               FROM client_items WHERE verified=1 AND taric_code IS NOT NULL AND taric_code != ''
               UNION ALL
               SELECT description_el, description_en, barcode, brand, quantity, categories,
                      analysis, taric_code, hs4
               FROM catalog WHERE verified=1 AND taric_code IS NOT NULL AND taric_code != ''"""
        ).fetchall()
        return [dict(r) for r in rows]


# --------------------------------------------------------- taric_nomenclature ----

def bulk_insert_taric(rows: list[TaricRow], version: str, source_url: str) -> int:
    with connect() as conn:
        conn.execute("DELETE FROM taric_nomenclature")
        conn.execute("DELETE FROM taric_nomenclature_fts")
        cur = conn.cursor()
        for r in rows:
            cur.execute(
                """INSERT INTO taric_nomenclature
                   (code, level, parent_code, description_el, description_en,
                    description_path_el, description_path_en, hs4, indent, unit,
                    valid_from, valid_to, source_version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (r.code, r.level, r.parent_code, r.description_el, r.description_en,
                 r.description_path_el, r.description_path_en, r.hs4,
                 r.indent, r.unit, r.valid_from, r.valid_to, version),
            )
            # Το FTS index περιλαμβάνει το ΠΛΗΡΕΣ path (γονικό context) για καλύτερο matching.
            cur.execute(
                "INSERT INTO taric_nomenclature_fts(rowid, text) VALUES (?, ?)",
                (int(cur.lastrowid), _fold(r.description_path_el or r.description_el,
                                           r.description_path_en or r.description_en, r.code)),
            )
        count = conn.execute("SELECT COUNT(*) AS n FROM taric_nomenclature").fetchone()["n"]
        conn.execute(
            """INSERT INTO taric_meta (id, version, imported_at, source_url, row_count)
               VALUES (1, ?, CURRENT_TIMESTAMP, ?, ?)
               ON CONFLICT(id) DO UPDATE SET version=excluded.version,
                 imported_at=excluded.imported_at, source_url=excluded.source_url,
                 row_count=excluded.row_count""",
            (version, source_url, count),
        )
        return int(count)


def taric_meta() -> Optional[dict[str, Any]]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM taric_meta WHERE id=1").fetchone()
        return dict(row) if row else None


def search_taric(text: str, limit: int = 25) -> list[TaricRow]:
    with connect() as conn:
        q = _fts_query(text)
        if q:
            try:
                rows = conn.execute(
                    """SELECT t.* FROM taric_nomenclature t
                       JOIN taric_nomenclature_fts f ON t.id=f.rowid
                       WHERE taric_nomenclature_fts MATCH ? ORDER BY rank LIMIT ?""",
                    (q, limit),
                ).fetchall()
                if rows:
                    return [_row_to_taric(r) for r in rows]
            except sqlite3.OperationalError:
                pass
        like = f"%{text.strip()}%"
        rows = conn.execute(
            """SELECT * FROM taric_nomenclature
               WHERE description_el LIKE ? OR description_en LIKE ? LIMIT ?""",
            (like, like, limit),
        ).fetchall()
        return [_row_to_taric(r) for r in rows]


def taric_row_count() -> int:
    with connect() as conn:
        return int(conn.execute("SELECT COUNT(*) AS n FROM taric_nomenclature").fetchone()["n"])


def iter_taric_texts() -> list[str]:
    """Όλες οι περιγραφές (path EL+EN) — για υπολογισμό IDF στο scoring."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT COALESCE(NULLIF(description_path_el,''), description_el) AS el,
                      COALESCE(NULLIF(description_path_en,''), description_en) AS en
               FROM taric_nomenclature"""
        ).fetchall()
        return [f"{r['el'] or ''} {r['en'] or ''}" for r in rows]


def all_taric_rows() -> list[TaricRow]:
    """Όλες οι γραμμές της ονοματολογίας ως TaricRow — για build embeddings."""
    with connect() as conn:
        rows = conn.execute("SELECT * FROM taric_nomenclature ORDER BY id").fetchall()
        return [_row_to_taric(r) for r in rows]


def get_taric_row(code: str) -> Optional[TaricRow]:
    """Μία γραμμή ονοματολογίας με ακριβή κωδικό (για retrieval μετά το embedding search)."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM taric_nomenclature WHERE code=? LIMIT 1", (code,)
        ).fetchone()
        return _row_to_taric(row) if row else None


def _row_to_taric(row: sqlite3.Row) -> TaricRow:
    keys = row.keys()
    return TaricRow(
        id=row["id"], code=row["code"] or "", level=row["level"] or 0,
        parent_code=row["parent_code"] or "", description_el=row["description_el"] or "",
        description_en=row["description_en"] or "",
        description_path_el=(row["description_path_el"] if "description_path_el" in keys else "") or "",
        description_path_en=(row["description_path_en"] if "description_path_en" in keys else "") or "",
        hs4=row["hs4"] or "", indent=row["indent"] or 0, unit=row["unit"] or "",
        valid_from=row["valid_from"] or "", valid_to=row["valid_to"] or "",
        source_version=row["source_version"] or "",
    )


# ------------------------------------------------------------------ ml_meta ----

def set_ml_meta(model_version: str, n_samples: int, cv_accuracy: float, algo: str) -> None:
    with connect() as conn:
        conn.execute(
            """INSERT INTO ml_meta (id, model_version, trained_at, n_samples, cv_accuracy, algo)
               VALUES (1, ?, CURRENT_TIMESTAMP, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET model_version=excluded.model_version,
                 trained_at=excluded.trained_at, n_samples=excluded.n_samples,
                 cv_accuracy=excluded.cv_accuracy, algo=excluded.algo""",
            (model_version, n_samples, cv_accuracy, algo),
        )


def get_ml_meta() -> Optional[dict[str, Any]]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM ml_meta WHERE id=1").fetchone()
        return dict(row) if row else None


def taric_source_breakdown(client_id: Optional[int] = None) -> dict[str, int]:
    """Πλήθος αποφάσεων ανά πηγή (ml/ai/fts/manual/web) — δείχνει τη μείωση εξάρτησης από AI."""
    with connect() as conn:
        if client_id is not None:
            rows = conn.execute(
                """SELECT taric_source, COUNT(*) AS n FROM client_items
                   WHERE client_id=? AND taric_code IS NOT NULL AND taric_code != ''
                   GROUP BY taric_source""",
                (client_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT taric_source, COUNT(*) AS n FROM client_items
                   WHERE taric_code IS NOT NULL AND taric_code != '' GROUP BY taric_source"""
            ).fetchall()
        return {(r["taric_source"] or "unknown"): r["n"] for r in rows}
