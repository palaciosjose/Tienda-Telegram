#!/usr/bin/env python3
"""Add shop_id column to discount_config and duplicate config per shop."""
import sqlite3
import db


def main():
    conn = db.get_db_connection()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(discount_config)")
    cols = [c[1] for c in cur.fetchall()]
    if 'shop_id' not in cols:
        cur.execute("ALTER TABLE discount_config ADD COLUMN shop_id INTEGER DEFAULT 1")
        print("✓ Columna 'shop_id' agregada a 'discount_config'")
    else:
        print("ℹ️ La tabla 'discount_config' ya tiene 'shop_id'")

    cur.execute("UPDATE discount_config SET shop_id = 1 WHERE shop_id IS NULL")

    cur.execute("SELECT id FROM shops")
    shop_ids = [r[0] for r in cur.fetchall()] or [1]

    cur.execute("SELECT discount_enabled, discount_text, discount_multiplier, show_fake_price FROM discount_config WHERE shop_id = 1 LIMIT 1")
    base = cur.fetchone() or (1, '🔥 DESCUENTOS ESPECIALES ACTIVOS 🔥', 1.5, 1)

    for sid in shop_ids:
        cur.execute("SELECT 1 FROM discount_config WHERE shop_id = ?", (sid,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO discount_config (discount_enabled, discount_text, discount_multiplier, show_fake_price, shop_id) VALUES (?, ?, ?, ?, ?)",
                (*base, sid),
            )
            print(f"✓ Configuración creada para shop_id {sid}")

    conn.commit()
    print("✓ Migración completada")


if __name__ == '__main__':
    main()
