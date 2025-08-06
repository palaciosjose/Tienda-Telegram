#!/usr/bin/env python3
"""Add group_ids column to campaign_schedules table."""
import sqlite3


def main():
    conn = sqlite3.connect('data/db/main_data.db')
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(campaign_schedules)")
    cols = [c[1] for c in cur.fetchall()]
    if 'group_ids' not in cols:
        cur.execute("ALTER TABLE campaign_schedules ADD COLUMN group_ids TEXT")
        print("\u2713 Columna 'group_ids' agregada a 'campaign_schedules'")
    else:
        print("\u2139\ufe0f La tabla 'campaign_schedules' ya tiene 'group_ids'")
    conn.commit()
    print("\u2713 Migraci\u00f3n completada")


if __name__ == '__main__':
    main()
