import sqlite3
import sys
import types
import json
import os

sys.path.append(os.getcwd())
import db

sys.modules.setdefault(
    "telebot",
    types.SimpleNamespace(
        TeleBot=lambda *a, **k: None,
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=lambda *a, **k: None,
            InlineKeyboardButton=lambda *a, **k: None,
        ),
    ),
)
sys.modules.setdefault(
    "advertising_system.auto_sender", types.SimpleNamespace(AutoSender=object)
)
sys.modules.setdefault(
    "advertising_system.telegram_multi",
    types.SimpleNamespace(TelegramMultiBot=lambda *a, **k: None),
)

from advertising_system.ad_manager import AdvertisingManager
from advertising_system.scheduler import CampaignScheduler


CREATE_CAMPAIGNS_TABLE = """CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    message_text TEXT NOT NULL,
    media_file_id TEXT,
    media_type TEXT,
    media_caption TEXT,
    button1_text TEXT,
    button1_url TEXT,
    button2_text TEXT,
    button2_url TEXT,
    status TEXT DEFAULT 'active',
    created_date TEXT,
    created_by INTEGER,
    shop_id INTEGER DEFAULT 1,
    daily_limit INTEGER DEFAULT 3,
    priority INTEGER DEFAULT 1
)"""

CREATE_SEND_LOGS_TABLE = """CREATE TABLE IF NOT EXISTS send_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    group_id TEXT,
    platform TEXT,
    status TEXT,
    sent_date TEXT,
    response_time REAL,
    error_message TEXT,
    shop_id INTEGER DEFAULT 1,
    FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
)"""

CREATE_TARGET_GROUPS_TABLE = """CREATE TABLE IF NOT EXISTS target_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    group_id TEXT NOT NULL,
    group_name TEXT,
    topic_id INTEGER,
    category TEXT,
    status TEXT DEFAULT 'active',
    last_sent TEXT,
    success_rate REAL DEFAULT 1.0,
    added_date TEXT,
    notes TEXT,
    shop_id INTEGER DEFAULT 1
)"""

CREATE_SCHEDULES_TABLE = """CREATE TABLE IF NOT EXISTS campaign_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    schedule_name TEXT,
    frequency TEXT,
    schedule_json TEXT,
    target_platforms TEXT,
    is_active INTEGER DEFAULT 1,
    next_send_telegram TEXT,
    created_date TEXT,
    shop_id INTEGER DEFAULT 1,
    group_ids TEXT,
    FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
)"""

CREATE_SHOPS_TABLE = """CREATE TABLE IF NOT EXISTS shops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    name TEXT
)"""


def init_ads_db(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(CREATE_SHOPS_TABLE)
    cur.execute(CREATE_CAMPAIGNS_TABLE)
    cur.execute(CREATE_SEND_LOGS_TABLE)
    cur.execute(CREATE_TARGET_GROUPS_TABLE)
    cur.execute(CREATE_SCHEDULES_TABLE)
    conn.commit()
    conn.close()


def test_create_campaign_inserts(tmp_path):
    db_path = tmp_path / "ads.db"
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))
    data = {"name": "Test Campaign", "message_text": "Hello", "created_by": 1}
    campaign_id = manager.create_campaign(data)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name, message_text, shop_id FROM campaigns WHERE id = ?", (campaign_id,))
    row = cur.fetchone()
    conn.close()

    assert row == ("Test Campaign", "Hello", 1)


def test_get_today_stats_empty_db(tmp_path):
    db_path = tmp_path / "ads.db"
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))

    stats = manager.get_today_stats()

    assert stats == {"sent": 0, "success_rate": 100, "groups": 0}


def test_send_campaign_now(tmp_path, monkeypatch):
    db_path = tmp_path / "ads.db"
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))

    camp_id = manager.create_campaign({"name": "Camp", "message_text": "Hi", "created_by": 1})
    manager.add_target_group("telegram", "111")

    sent = []

    class DummyTG:
        def __init__(self, *a, **k):
            pass

        def send_message(self, gid, msg, media_file_id=None, media_type=None, buttons=None):
            sent.append(("tg", gid, msg))
            return True, "ok"


    import advertising_system.ad_manager as mod
    monkeypatch.setattr(mod, "TelegramMultiBot", DummyTG)
    monkeypatch.setenv("TELEGRAM_TOKEN", "x")

    ok, msg = manager.send_campaign_now(camp_id, ["telegram"])
    assert ok
    assert msg == "Campaña enviada"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT platform, status, shop_id FROM send_logs ORDER BY id")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 1
    assert sent == [("tg", "111", "Hi")]
    assert all(r[1] == "sent" for r in rows)
    assert all(r[2] == 1 for r in rows)


def test_schedule_campaign_records_json(tmp_path):
    db_path = tmp_path / "ads.db"
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))
    camp_id = manager.create_campaign({"name": "Camp2", "message_text": "Hi", "created_by": 1})

    ok, msg = manager.schedule_campaign(camp_id, ["lunes"], ["10:00", "15:00"])
    assert ok

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT schedule_json FROM campaign_schedules WHERE campaign_id = ?", (camp_id,))
    row = cur.fetchone()
    conn.close()
    assert row is not None
    data = json.loads(row[0])
    assert data == {"lunes": ["10:00", "15:00"]}


def test_update_campaign_updates_text(tmp_path):
    db_path = tmp_path / "ads.db"
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))

    camp_id = manager.create_campaign({"name": "CampU", "message_text": "Hi", "created_by": 1})
    ok = manager.update_campaign(camp_id, {"message_text": "Bye"})
    assert ok

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT message_text, shop_id FROM campaigns WHERE id = ?", (camp_id,))
    row = cur.fetchone()
    conn.close()
    assert row == ("Bye", 1)


def test_send_campaign_now_failure(tmp_path, monkeypatch):
    db_path = tmp_path / "ads.db"
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))

    camp_id = manager.create_campaign({"name": "Camp", "message_text": "Hi", "created_by": 1})
    manager.add_target_group("telegram", "111")

    class DummyTG:
        def __init__(self, *a, **k):
            pass

        def send_message(self, *a, **k):
            return False, "err"

    import advertising_system.ad_manager as mod
    monkeypatch.setattr(mod, "TelegramMultiBot", DummyTG)
    monkeypatch.setenv("TELEGRAM_TOKEN", "x")

    ok, msg = manager.send_campaign_now(camp_id, ["telegram"])
    assert not ok
    assert msg == "err"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT status, error_message, shop_id FROM send_logs")
    rows = cur.fetchall()
    conn.close()

    assert rows == [("failed", "err", 1)]


def test_send_campaign_to_group_fails(tmp_path, monkeypatch):
    db_path = tmp_path / "ads.db"
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))

    camp_id = manager.create_campaign({"name": "Camp", "message_text": "Hi", "created_by": 1})

    class DummyTG:
        def __init__(self, *a, **k):
            pass

        def send_message(self, *a, **k):
            return False, "err"

    import advertising_system.ad_manager as mod
    monkeypatch.setattr(mod, "TelegramMultiBot", DummyTG)
    monkeypatch.setenv("TELEGRAM_TOKEN", "x")

    ok, msg = manager.send_campaign_to_group(camp_id, "999")
    assert not ok
    assert msg == "err"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT status, error_message, shop_id FROM send_logs")
    rows = cur.fetchall()
    conn.close()

    assert rows == [("failed", "err", 1)]


def test_get_target_groups_only_active(tmp_path):
    db_path = tmp_path / "ads.db"
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))

    manager.add_target_group("telegram", "111", "GroupA")
    manager.add_target_group("telegram", "222", "GroupB")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE target_groups SET status='blocked' WHERE group_id='222'")
    conn.commit()
    conn.close()

    groups = manager.get_target_groups()
    assert groups == [{"id": 1, "group_id": "111", "group_name": "GroupA", "topic_id": None}]


def test_add_target_group_with_topic(tmp_path):
    db_path = tmp_path / "ads.db"
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))

    ok, msg = manager.add_target_group("telegram", "333", "TopicGroup", topic_id=10)
    assert ok

    groups = manager.get_target_groups()
    assert groups == [{"id": 1, "group_id": "333", "group_name": "TopicGroup", "topic_id": 10}]


def test_delete_campaign_removes_record(tmp_path):
    db_path = tmp_path / "ads.db"
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))

    camp_id = manager.create_campaign({"name": "DelMe", "message_text": "Hi", "created_by": 1})

    ok = manager.delete_campaign(camp_id)
    assert ok

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM campaigns WHERE id = ?", (camp_id,))
    count = cur.fetchone()[0]
    conn.close()

    assert count == 0


def test_deactivate_schedule_removes_from_pending(tmp_path, monkeypatch):
    db_path = tmp_path / "ads.db"
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))

    camp_id = manager.create_campaign({"name": "Camp", "message_text": "Hi", "created_by": 1})
    ok, _ = manager.schedule_campaign(camp_id, ["lunes"], ["10:00"])
    assert ok

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM campaign_schedules")
    schedule_id = cur.fetchone()[0]
    conn.close()

    import advertising_system.scheduler as mod
    class DummyDatetime(mod.datetime):
        @classmethod
        def now(cls):
            return cls(2023, 1, 2, 10, 0)

    monkeypatch.setattr(mod, "datetime", DummyDatetime)

    scheduler = CampaignScheduler(str(db_path))
    assert len(scheduler.get_pending_sends()) == 1

    manager.deactivate_schedule(schedule_id)
    assert scheduler.get_pending_sends() == []


def test_update_global_limit(tmp_path, monkeypatch):
    import files
    monkeypatch.setattr(files, "main_db", str(tmp_path / "main.db"))
    conn = sqlite3.connect(files.main_db)
    conn.execute(
        "CREATE TABLE global_config (key TEXT PRIMARY KEY, value TEXT)"
    )
    conn.commit()
    conn.close()

    db.update_global_limit("daily_limit", "5")
    status = db.get_global_telethon_status()
    assert status.get("daily_limit") == "5"

    db.update_global_limit("daily_limit", "7")
    status = db.get_global_telethon_status()
    assert status.get("daily_limit") == "7"

