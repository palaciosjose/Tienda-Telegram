#!/usr/bin/env python3
"""Create shop_users table if it doesn't exist."""
import db


def main():
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shop_users'")
    if cur.fetchone() is None:
        cur.execute(
            "CREATE TABLE shop_users (user_id INTEGER PRIMARY KEY, shop_id INTEGER DEFAULT 1)"
        )
        print("✓ Tabla 'shop_users' creada")
    else:
        print("ℹ️ La tabla 'shop_users' ya existe")
    conn.commit()
    print("✓ Migración completada")


if __name__ == "__main__":
    main()
