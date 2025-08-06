#!/usr/bin/env python3
"""Create bot_groups table."""
import db


def main():
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_groups'")
    if cur.fetchone() is None:
        cur.execute(
            """CREATE TABLE bot_groups (
                group_id TEXT PRIMARY KEY,
                group_name TEXT,
                added_date TEXT
            )"""
        )
        print("✓ Tabla 'bot_groups' creada")
    else:
        print("ℹ️ La tabla 'bot_groups' ya existe")
    conn.commit()
    print("✓ Migración completada")


if __name__ == "__main__":
    main()
