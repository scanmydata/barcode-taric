"""SQLite σύνδεση, schema & migrations (με FTS5 full-text search).

Ένα αρχείο βάσης ανά-χρήστη στο data-dir. Πίνακες:
  clients, catalog(+catalog_fts), client_items,
  taric_nomenclature(+taric_nomenclature_fts), taric_meta, ml_meta.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import db_path

SCHEMA_VERSION = 1


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path or db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _has_fts5(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts_probe USING fts5(x)")
        conn.execute("DROP TABLE IF EXISTS _fts_probe")
        return True
    except sqlite3.OperationalError:
        return False


def init_db(path: Path | None = None) -> None:
    """Δημιουργεί/αναβαθμίζει το schema. Ασφαλές να κληθεί σε κάθε εκκίνηση."""
    with connect(path) as conn:
        c = conn.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                vat TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT UNIQUE,
                description_el TEXT,
                description_en TEXT,
                taric_code TEXT,
                hs4 TEXT,
                taric_description TEXT,
                confidence REAL DEFAULT 0,
                ai_rationale TEXT,
                taric_source TEXT,
                verified INTEGER DEFAULT 0,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS client_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                barcode TEXT,
                description_el TEXT,
                description_en TEXT,
                taric_code TEXT,
                hs4 TEXT,
                taric_description TEXT,
                confidence REAL DEFAULT 0,
                ai_rationale TEXT,
                taric_source TEXT,
                verified INTEGER DEFAULT 0,
                source TEXT,
                catalog_id INTEGER REFERENCES catalog(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(client_id, barcode)
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_client_items_client ON client_items(client_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_client_items_taric ON client_items(taric_code)")

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS taric_nomenclature (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                level INTEGER DEFAULT 0,
                parent_code TEXT,
                description_el TEXT,
                description_en TEXT,
                description_path_el TEXT,
                description_path_en TEXT,
                hs4 TEXT,
                indent INTEGER DEFAULT 0,
                unit TEXT,
                valid_from TEXT,
                valid_to TEXT,
                source_version TEXT
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_taric_code ON taric_nomenclature(code)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_taric_hs4 ON taric_nomenclature(hs4)")

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS taric_meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version TEXT,
                imported_at TIMESTAMP,
                source_url TEXT,
                row_count INTEGER DEFAULT 0
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS ml_meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                model_version TEXT,
                trained_at TIMESTAMP,
                n_samples INTEGER DEFAULT 0,
                cv_accuracy REAL DEFAULT 0,
                algo TEXT
            )
            """
        )

        if _has_fts5(conn):
            # Standalone FTS5 tables με ΕΝΑ folded (χωρίς τόνους, πεζό) column που
            # γεμίζει το repo από Python — δεν εξαρτόμαστε από τον tokenizer για την
            # αφαίρεση ελληνικών τόνων (ο unicode61 δεν folds τα precomposed ά/έ/…).
            # rowid = id του βασικού πίνακα, ώστε να γίνεται join.
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS catalog_fts USING fts5(text)")
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS taric_nomenclature_fts USING fts5(text)")

        # Lightweight migrations: πρόσθεσε λεπτομέρειες προϊόντος (brand/quantity/categories)
        # σε υπάρχουσες βάσεις χωρίς απώλεια δεδομένων.
        for table in ("catalog", "client_items"):
            _ensure_columns(c, table, {
                "brand": "TEXT", "quantity": "TEXT", "categories": "TEXT",
                "analysis": "TEXT",   # δομημένη ανάλυση προϊόντος (tariff hint + ML feature)
            })
        _ensure_columns(c, "taric_nomenclature", {
            "description_path_el": "TEXT", "description_path_en": "TEXT",
        })

        c.execute("PRAGMA user_version = %d" % SCHEMA_VERSION)


def _ensure_columns(cursor, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, decl in columns.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def has_fts5(path: Path | None = None) -> bool:
    with connect(path) as conn:
        return _has_fts5(conn)
