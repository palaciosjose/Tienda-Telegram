#!/usr/bin/env python3
"""Add description and media/button fields to shops table."""
import db


def main():
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(shops)")
    cols = [c[1] for c in cur.fetchall()]
    mappings = [
        ("description", "TEXT"),
        ("media_file_id", "TEXT"),
        ("media_type", "TEXT"),
        ("button1_text", "TEXT"),
        ("button1_url", "TEXT"),
        ("button2_text", "TEXT"),
        ("button2_url", "TEXT"),
    ]
    for col, ctype in mappings:
        if col not in cols:
            cur.execute(f"ALTER TABLE shops ADD COLUMN {col} {ctype}")
            print(f"✓ Columna '{col}' agregada a 'shops'")
        else:
            print(f"ℹ️ La tabla 'shops' ya tiene '{col}'")
    conn.commit()
    print("✓ Migración completada")


if __name__ == "__main__":
    main()
