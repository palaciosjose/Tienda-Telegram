#!/usr/bin/env python3
"""Add telethon and campaign limit columns plus new tables."""
import db


def main():
    conn = db.get_db_connection()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(shops)")
    cols = [c[1] for c in cur.fetchall()]
    if "telethon_enabled" not in cols:
        cur.execute(
            "ALTER TABLE shops ADD COLUMN telethon_enabled INTEGER DEFAULT 0"
        )
    if "telethon_api_id" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_api_id TEXT")
    if "telethon_api_hash" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_api_hash TEXT")
    if "telethon_phone" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_phone TEXT")
    if "telethon_bridge_group" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_bridge_group TEXT")
    if "telethon_daemon_status" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_daemon_status TEXT")
    if "telethon_last_activity" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_last_activity TEXT")
    if "max_campaigns_daily" not in cols:
        cur.execute(
            "ALTER TABLE shops ADD COLUMN max_campaigns_daily INTEGER DEFAULT 0"
        )
    if "current_campaigns_today" not in cols:
        cur.execute(
            "ALTER TABLE shops ADD COLUMN current_campaigns_today INTEGER DEFAULT 0"
        )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS store_topics (
            store_id INTEGER,
            group_id TEXT,
            group_name TEXT,
            topic_id INTEGER,
            topic_name TEXT
        )
        """
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS global_config (key TEXT PRIMARY KEY, value TEXT)"
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS unified_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            level TEXT,
            message TEXT,
            store_id INTEGER
        )
        """
    )
    conn.commit()
    print("✓ Migración completada")


if __name__ == "__main__":
    main()
