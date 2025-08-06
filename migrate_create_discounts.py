#!/usr/bin/env python3
"""Create discounts table."""
import db


def main():
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS discounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            percent INTEGER,
            start_time TEXT,
            end_time TEXT,
            category_id INTEGER,
            shop_id INTEGER
        )
        """
    )
    conn.commit()
    print("✓ Tabla 'discounts' creada")


if __name__ == "__main__":
    main()
