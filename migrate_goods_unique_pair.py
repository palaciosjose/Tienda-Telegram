#!/usr/bin/env python3
"""Migrate goods table to have (name, shop_id) as primary key and update stored file paths."""
import os
import sqlite3
import db


def main():
    conn = db.get_db_connection()
    cur = conn.cursor()

    # Check if table already migrated
    cur.execute("PRAGMA table_info(goods)")
    cols = cur.fetchall()
    pk_cols = [c[1] for c in cols if c[-1]]
    if set(pk_cols) == {"name", "shop_id"}:
        print("ℹ️ La tabla 'goods' ya usa (name, shop_id) como clave primaria")
        return

    # Ensure shop_id column exists
    if not any(c[1] == "shop_id" for c in cols):
        cur.execute("ALTER TABLE goods ADD COLUMN shop_id INTEGER DEFAULT 1")
        print("✓ Columna 'shop_id' agregada a 'goods'")

    # Rename old table
    cur.execute("ALTER TABLE goods RENAME TO goods_old")

    # Create new table with composite primary key
    cur.execute(
        """
        CREATE TABLE goods (
            name TEXT,
            description TEXT,
            format TEXT,
            minimum INTEGER,
            price INTEGER,
            stored TEXT,
            additional_description TEXT DEFAULT '',
            media_file_id TEXT,
            media_type TEXT,
            media_caption TEXT,
            duration_days INTEGER DEFAULT NULL,
            manual_delivery INTEGER DEFAULT 0,
            category_id INTEGER,
            shop_id INTEGER DEFAULT 1,
            PRIMARY KEY (name, shop_id)
        )
        """
    )

    cur.execute(
        "INSERT INTO goods SELECT name, description, format, minimum, price, stored,"
        " additional_description, media_file_id, media_type, media_caption,"
        " duration_days, manual_delivery, category_id, shop_id FROM goods_old"
    )

    # Move stored files
    cur.execute("SELECT name, stored, shop_id FROM goods")
    rows = cur.fetchall()
    for name, stored, shop_id in rows:
        if not stored:
            continue
        prefix = f"data/goods/{shop_id}_"
        desired = f"{prefix}{name}.txt"
        if stored != desired and os.path.exists(stored):
            os.makedirs(os.path.dirname(desired), exist_ok=True)
            os.rename(stored, desired)
            cur.execute(
                "UPDATE goods SET stored = ? WHERE name = ? AND shop_id = ?",
                (desired, name, shop_id),
            )

    conn.commit()
    cur.execute("DROP TABLE goods_old")
    conn.commit()
    print("✓ Migración completada")


if __name__ == "__main__":
    main()
