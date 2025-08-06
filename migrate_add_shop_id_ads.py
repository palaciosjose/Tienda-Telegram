#!/usr/bin/env python3
"""Add shop_id column to advertising tables if missing."""
import sqlite3


def main():
    conn = sqlite3.connect('data/db/main_data.db')
    cur = conn.cursor()

    tables = [
        'send_logs',
        'target_groups',
        'campaign_schedules',
        'platform_config',
        'daily_stats',
        'rate_limit_logs',
    ]

    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        cols = [c[1] for c in cur.fetchall()]
        if 'shop_id' not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN shop_id INTEGER DEFAULT 1")
            print(f"✓ Columna 'shop_id' agregada a '{table}'")
        else:
            print(f"ℹ️ La tabla '{table}' ya tiene 'shop_id'")

    conn.commit()
    print("✓ Migración completada")


if __name__ == '__main__':
    main()
