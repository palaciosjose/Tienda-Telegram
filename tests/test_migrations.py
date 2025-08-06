import importlib
import sqlite3
import sys
import os

sys.path.append(os.getcwd())

import files


def test_migration_adds_columns_and_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "main.db"
    monkeypatch.setattr(files, "main_db", str(db_path))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_ADMIN_ID", "1")
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com")
    import db
    db.close_connection()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE shops (id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, name TEXT)")
    conn.commit()
    conn.close()

    module = importlib.import_module("migrate_add_telethon_columns")
    module.main()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(shops)")
    cols = [c[1] for c in cur.fetchall()]
    for col in [
        "telethon_enabled",
        "telethon_api_id",
        "telethon_api_hash",
        "telethon_phone",
        "telethon_bridge_group",
        "telethon_daemon_status",
        "telethon_last_activity",
        "max_campaigns_daily",
        "current_campaigns_today",
    ]:
        assert col in cols

    for table in ["store_topics", "global_config", "unified_logs"]:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        assert cur.fetchone() is not None
    conn.close()
