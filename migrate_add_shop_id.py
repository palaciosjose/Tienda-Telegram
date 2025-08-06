#!/usr/bin/env python3
"""Add shop_id column to purchases and buyers tables."""
import sqlite3
import db

def main():
    conn = db.get_db_connection()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(purchases)")
    cols = [c[1] for c in cur.fetchall()]
    if 'shop_id' not in cols:
        cur.execute("ALTER TABLE purchases ADD COLUMN shop_id INTEGER DEFAULT 1")
        print("✓ Columna 'shop_id' agregada a 'purchases'")
    else:
        print("ℹ️ La tabla 'purchases' ya tiene 'shop_id'")

    cur.execute("PRAGMA table_info(buyers)")
    cols = [c[1] for c in cur.fetchall()]
    if 'shop_id' not in cols:
        cur.execute("ALTER TABLE buyers ADD COLUMN shop_id INTEGER DEFAULT 1")
        print("✓ Columna 'shop_id' agregada a 'buyers'")
    else:
        print("ℹ️ La tabla 'buyers' ya tiene 'shop_id'")

    conn.commit()
    print("✓ Migración completada")

if __name__ == "__main__":
    main()
