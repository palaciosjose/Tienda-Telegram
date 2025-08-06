#!/usr/bin/env python3
"""Add topic_id column to target_groups table."""
import sqlite3


def main():
    conn = sqlite3.connect('data/db/main_data.db')
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(target_groups)")
    cols = [c[1] for c in cur.fetchall()]
    if 'topic_id' not in cols:
        cur.execute("ALTER TABLE target_groups ADD COLUMN topic_id INTEGER")
        print("✓ Columna 'topic_id' agregada a 'target_groups'")
    else:
        print("ℹ️ La tabla 'target_groups' ya tiene 'topic_id'")
    conn.commit()
    print("✓ Migración completada")


if __name__ == '__main__':
    main()
