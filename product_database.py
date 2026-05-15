#!/usr/bin/env python3
"""SQLite database for storing products, barcodes, descriptions, and TARIC codes."""

import os
import sqlite3
import tempfile
import secrets
from pathlib import Path
from typing import Any, Optional, List
from dataclasses import dataclass
import json
from contextlib import contextmanager

from cryptography.fernet import Fernet, InvalidToken

DOTENV_PATH = Path(".env")
DB_FOLDER = Path("db")
DB_PATH = DB_FOLDER / "product_database.db.enc"


def _debug(message: str) -> None:
    """Print debug message (can be redirected via environment variables)."""
    import os
    if os.getenv("DEBUG"):
        print(f"[DB DEBUG] {message}")


def _load_dotenv(dotenv_path: Path = DOTENV_PATH) -> None:
    if not dotenv_path.is_file():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _ensure_encryption_key(dotenv_path: Path = DOTENV_PATH) -> bytes:
    _load_dotenv(dotenv_path)
    key = os.getenv("DB_ENCRYPTION_KEY")
    if key:
        return key.encode("utf-8")

    key_bytes = Fernet.generate_key()
    key_text = key_bytes.decode("utf-8")
    dotenv_path.parent.mkdir(parents=True, exist_ok=True)
    if dotenv_path.exists():
        dotenv_path.write_text(dotenv_path.read_text(encoding="utf-8") + f"\nDB_ENCRYPTION_KEY={key_text}\n", encoding="utf-8")
    else:
        dotenv_path.write_text(f"DB_ENCRYPTION_KEY={key_text}\n", encoding="utf-8")
    os.environ["DB_ENCRYPTION_KEY"] = key_text
    return key_bytes


def _get_cipher() -> Fernet:
    key = os.getenv("DB_ENCRYPTION_KEY")
    if not key:
        key_bytes = _ensure_encryption_key(DOTENV_PATH)
        return Fernet(key_bytes)
    return Fernet(key.encode("utf-8"))


def _decrypt_database(db_path: Path) -> Path:
    DB_FOLDER.mkdir(parents=True, exist_ok=True)
    temp_handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_path = Path(temp_handle.name)
    temp_handle.close()

    if not db_path.exists():
        temp_path.write_bytes(b"")
        return temp_path

    cipher = _get_cipher()
    encrypted_data = db_path.read_bytes()
    try:
        plaintext = cipher.decrypt(encrypted_data)
    except InvalidToken as exc:
        raise ValueError("Invalid database encryption key or corrupted database file") from exc
    temp_path.write_bytes(plaintext)
    return temp_path


def _encrypt_database(plain_path: Path, encrypted_path: Path) -> None:
    cipher = _get_cipher()
    plaintext = plain_path.read_bytes()
    encrypted = cipher.encrypt(plaintext)
    encrypted_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = encrypted_path.with_suffix(encrypted_path.suffix + ".tmp")
    tmp_path.write_bytes(encrypted)
    tmp_path.replace(encrypted_path)


@contextmanager
def _decrypted_database(db_path: Path = DB_PATH):
    plain_path = _decrypt_database(db_path)
    try:
        yield plain_path
    finally:
        if plain_path.exists():
            _encrypt_database(plain_path, db_path)
            plain_path.unlink(missing_ok=True)


@dataclass
class ProductRecord:
    barcode: Optional[str]
    product_name: str
    description: str
    commercial_text: str
    customs_text: str
    taric_code: Optional[str]
    hs4: Optional[str]
    taric_description: str
    source: str


def init_database(db_path: Path = DB_PATH) -> None:
    """Initialize SQLite database with product records."""
    with _decrypted_database(db_path) as decrypted_path:
        conn = sqlite3.connect(decrypted_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT UNIQUE,
                product_name TEXT NOT NULL,
                description TEXT,
                commercial_text TEXT,
                customs_text TEXT,
                taric_code TEXT,
                hs4 TEXT,
                taric_description TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create FTS5 virtual table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
                product_name,
                description,
                commercial_text,
                customs_text,
                content=products,
                content_rowid=id
            )
        """)
        
        conn.commit()
        conn.close()


def add_product(
    product: ProductRecord,
    db_path: Path = DB_PATH
) -> bool:
    """Add or update a product record in the database."""
    init_database(db_path)
    with _decrypted_database(db_path) as decrypted_path:
        conn = sqlite3.connect(decrypted_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO products 
                (barcode, product_name, description, commercial_text, customs_text, taric_code, hs4, taric_description, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product.barcode,
                product.product_name,
                product.description,
                product.commercial_text,
                product.customs_text,
                product.taric_code,
                product.hs4,
                product.taric_description,
                product.source
            ))
            
            # Always update FTS index (get the id of the inserted/updated row)
            # For products with barcode, search by barcode; otherwise search by customs_text
            if product.barcode:
                cursor.execute("SELECT id FROM products WHERE barcode = ?", (product.barcode,))
            else:
                cursor.execute("SELECT id FROM products WHERE customs_text = ? ORDER BY id DESC LIMIT 1", (product.customs_text,))
            
            row_id = cursor.fetchone()
            if row_id:
                cursor.execute("""
                    INSERT OR REPLACE INTO products_fts(rowid, product_name, description, commercial_text, customs_text)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    row_id[0],
                    product.product_name or "",
                    product.description or "",
                    product.commercial_text or "",
                    product.customs_text or ""
                ))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()


def search_by_barcode(barcode: str, db_path: Path = DB_PATH) -> Optional[ProductRecord]:
    """Search for a product by barcode."""
    init_database(db_path)
    with _decrypted_database(db_path) as decrypted_path:
        conn = sqlite3.connect(decrypted_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT barcode, product_name, description, commercial_text, customs_text, 
                       taric_code, hs4, taric_description, source
                FROM products
                WHERE barcode = ?
            """, (barcode,))
            
            row = cursor.fetchone()
            if row:
                return ProductRecord(*row)
            return None
        finally:
            conn.close()


def search_by_description(
    search_text: str,
    limit: int = 10,
    db_path: Path = DB_PATH
) -> List[ProductRecord]:
    """Full-text search by product description/name."""
    init_database(db_path)
    with _decrypted_database(db_path) as decrypted_path:
        conn = sqlite3.connect(decrypted_path)
        cursor = conn.cursor()
        
        try:
            # Prepare search terms - FTS5 expects bare words, no wildcards
            # Split by whitespace and join with OR
            search_terms = " OR ".join(word.strip() for word in search_text.split() if word.strip())
            
            if not search_terms:
                return []
            
            try:
                cursor.execute("""
                    SELECT p.barcode, p.product_name, p.description, p.commercial_text, p.customs_text,
                           p.taric_code, p.hs4, p.taric_description, p.source
                    FROM products p
                    JOIN products_fts fts ON p.id = fts.rowid
                    WHERE products_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (search_terms, limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append(ProductRecord(*row))
                return results
            except sqlite3.OperationalError as e:
                # Fallback to simple LIKE search if FTS5 fails
                _debug(f"FTS5 search failed: {e}, falling back to LIKE")
                return _search_by_like(search_text, limit, cursor)
        finally:
            conn.close()


def _search_by_like(search_text: str, limit: int, cursor: sqlite3.Cursor) -> List[ProductRecord]:
    """Fallback LIKE-based search when FTS5 fails."""
    try:
        # Escape special characters for LIKE
        search_term = f"%{search_text}%"
        
        cursor.execute("""
            SELECT barcode, product_name, description, commercial_text, customs_text,
                   taric_code, hs4, taric_description, source
            FROM products
            WHERE product_name LIKE ? OR description LIKE ? OR commercial_text LIKE ? OR customs_text LIKE ?
            LIMIT ?
        """, (search_term, search_term, search_term, search_term, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append(ProductRecord(*row))
        return results
    except Exception as e:
        _debug(f"LIKE search also failed: {e}")
        return []


def get_all_products(db_path: Path = DB_PATH) -> List[ProductRecord]:
    """Get all products from database."""
    init_database(db_path)
    with _decrypted_database(db_path) as decrypted_path:
        conn = sqlite3.connect(decrypted_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT barcode, product_name, description, commercial_text, customs_text,
                       taric_code, hs4, taric_description, source
                FROM products
                ORDER BY created_at DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append(ProductRecord(*row))
            return results
        finally:
            conn.close()


def list_products_detailed(db_path: Path = DB_PATH) -> None:
    """Print all products with full details (Date/Time, TARIC, Barcode, Description)."""
    init_database(db_path)
    with _decrypted_database(db_path) as decrypted_path:
        conn = sqlite3.connect(decrypted_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    created_at,
                    barcode,
                    taric_code,
                    hs4,
                    product_name,
                    description,
                    commercial_text,
                    customs_text,
                    taric_description,
                    source
                FROM products
                ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            if not rows:
                print("📭 No products in database yet.")
                return
            
            print("\n" + "="*120)
            print(f"{'📊 PRODUCT DATABASE - Complete Details':^120}")
            print("="*120)
            
            for idx, row in enumerate(rows, 1):
                created_at, barcode, taric_code, hs4, product_name, description, commercial_text, customs_text, taric_description, source = row
                
                print(f"\n[{idx}] ⏰ DATE/TIME: {created_at}")
                print(f"    🏷️  BARCODE: {barcode or '(No barcode)'}")
                print(f"    📦 TARIC CODE: {taric_code or '(No TARIC match)'}")
                print(f"    📝 HS4: {hs4 or 'N/A'}")
                print(f"    🎯 TARIC DESCRIPTION: {taric_description}")
                print(f"    📌 PRODUCT NAME: {product_name or '(No name)'}")
                print(f"    📄 DESCRIPTION: {description or '(No description)'}")
                print(f"    🛒 COMMERCIAL TEXT: {commercial_text}")
                print(f"    🔧 CUSTOMS TEXT: {customs_text}")
                print(f"    🔗 SOURCE: {source}")
                print("-"*120)
            
            print(f"\n✅ Total: {len(rows)} product(s) in database\n")
        finally:
            conn.close()


def export_database_to_json(output_path: Path = Path("product_database.json"), db_path: Path = DB_PATH) -> None:
    """Export entire database to JSON for backup."""
    products = get_all_products(db_path)
    data = []
    for p in products:
        data.append({
            "barcode": p.barcode,
            "product_name": p.product_name,
            "description": p.description,
            "commercial_text": p.commercial_text,
            "customs_text": p.customs_text,
            "taric_code": p.taric_code,
            "hs4": p.hs4,
            "taric_description": p.taric_description,
            "source": p.source
        })
    
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {len(data)} products to {output_path}")


def import_database_from_json(input_path: Path, db_path: Path = DB_PATH) -> None:
    """Import products from JSON to database."""
    data = json.loads(input_path.read_text(encoding="utf-8"))
    
    for item in data:
        product = ProductRecord(
            barcode=item.get("barcode"),
            product_name=item.get("product_name", ""),
            description=item.get("description", ""),
            commercial_text=item.get("commercial_text", ""),
            customs_text=item.get("customs_text", ""),
            taric_code=item.get("taric_code"),
            hs4=item.get("hs4"),
            taric_description=item.get("taric_description", ""),
            source=item.get("source", "import")
        )
        add_product(product, db_path)
    
    print(f"Imported {len(data)} products from {input_path}")


if __name__ == "__main__":
    init_database()
    print(f"Database initialized at {DB_PATH}")
