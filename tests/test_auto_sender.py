import importlib
import sys
import sqlite3
import json
import types


def test_check_and_send_campaigns_returns_bool(tmp_path, monkeypatch):
    # Reload the real module in case previous tests inserted a stub
    sys.modules.pop('advertising_system.auto_sender', None)
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub)
    auto_sender = importlib.import_module('advertising_system.auto_sender')
    AutoSender = auto_sender.AutoSender

    config = {
        'db_path': str(tmp_path / 'db.db'),
        'telegram_tokens': ['t']
    }
    sender = AutoSender(config)

    # Avoid actual delays
    monkeypatch.setattr(auto_sender.time, 'sleep', lambda x: None)

    calls = []
    monkeypatch.setattr(sender, '_send_telegram_campaign_corrected', lambda *a, **k: (calls.append('tg') or True))

    sender.scheduler.get_pending_sends = lambda: [(1, 2, None, None, None, 'telegram')]
    assert sender._check_and_send_campaigns() is True
    assert calls == ['tg']

    calls.clear()
    sender.scheduler.get_pending_sends = lambda: []
    assert sender._check_and_send_campaigns() is False
    assert calls == []


def test_check_and_send_campaigns_none_platforms(tmp_path, monkeypatch):
    sys.modules.pop('advertising_system.auto_sender', None)
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub)
    auto_sender = importlib.import_module('advertising_system.auto_sender')
    AutoSender = auto_sender.AutoSender

    config = {
        'db_path': str(tmp_path / 'db.db'),
        'telegram_tokens': ['t']
    }
    sender = AutoSender(config)

    monkeypatch.setattr(auto_sender.time, 'sleep', lambda x: None)
    calls = []
    monkeypatch.setattr(sender, '_send_telegram_campaign_corrected', lambda *a, **k: (calls.append('tg') or True))

    sender.scheduler.get_pending_sends = lambda: [(1, 2, None, None, None, None)]
    assert sender._check_and_send_campaigns() is False
    assert calls == []


def test_check_and_send_campaigns_with_mocked_dependencies(monkeypatch):
    sys.modules.pop('advertising_system.auto_sender', None)
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub)
    auto_sender = importlib.import_module('advertising_system.auto_sender')

    class DummyScheduler:
        def __init__(self, db_path, shop_id=1):
            pass

        def get_pending_sends(self):
            return [(1, 2, None, None, None, 'telegram')]

        def update_next_send(self, *a):
            pass

    class DummyRateLimiter:
        def __init__(self, db_path, shop_id=1):
            pass

    class DummyStats:
        def __init__(self, db_path, shop_id=1):
            pass

    monkeypatch.setattr(auto_sender, 'CampaignScheduler', DummyScheduler)
    monkeypatch.setattr(auto_sender, 'IntelligentRateLimiter', DummyRateLimiter)
    monkeypatch.setattr(auto_sender, 'StatisticsManager', DummyStats)
    monkeypatch.setattr(auto_sender, 'TelegramMultiBot', lambda *a, **k: object())

    AutoSender = auto_sender.AutoSender

    config = {
        'db_path': 'db',
        'telegram_tokens': ['t']
    }
    sender = AutoSender(config)

    monkeypatch.setattr(auto_sender.time, 'sleep', lambda x: None)
    calls = []
    monkeypatch.setattr(sender, '_send_telegram_campaign_corrected', lambda *a, **k: (calls.append('tg') or True))

    assert sender._check_and_send_campaigns() is True
    assert calls == ['tg']

    calls.clear()
    sender.scheduler.get_pending_sends = lambda: []
    assert sender._check_and_send_campaigns() is False
    assert calls == []


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

CREATE_SHOPS_TABLE = """CREATE TABLE IF NOT EXISTS shops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    name TEXT
)"""

CREATE_SCHEDULES_TABLE_NOGID = """CREATE TABLE campaign_schedules (
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
    FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
)"""


class DummyTeleBot:
    calls = []

    def __init__(self, token):
        pass

    def send_message(self, chat_id, text, **kw):
        DummyTeleBot.calls.append(chat_id)
        return True, "ok"


telebot_stub = types.SimpleNamespace(
    TeleBot=DummyTeleBot,
    types=types.SimpleNamespace(
        InlineKeyboardMarkup=lambda *a, **k: None,
        InlineKeyboardButton=lambda *a, **k: None,
    ),
)


def _init_db_no_gid(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(CREATE_SHOPS_TABLE)
    cur.execute(CREATE_CAMPAIGNS_TABLE)
    cur.execute(CREATE_TARGET_GROUPS_TABLE)
    cur.execute("CREATE TABLE goods (name TEXT, description TEXT, price REAL, media_file_id TEXT, media_type TEXT, shop_id INTEGER DEFAULT 1)")
    cur.execute(CREATE_SCHEDULES_TABLE_NOGID)
    conn.commit()
    conn.close()


def test_send_without_group_ids_column(tmp_path, monkeypatch):
    DummyTeleBot.calls.clear()
    monkeypatch.setitem(sys.modules, "telebot", telebot_stub)
    sys.modules.pop('advertising_system.telegram_multi', None)
    sys.modules.pop('advertising_system.auto_sender', None)
    auto_mod = importlib.import_module('advertising_system.auto_sender')
    AutoSender = auto_mod.AutoSender

    db_path = tmp_path / 'ads.db'
    _init_db_no_gid(db_path)

    manager_mod = importlib.import_module('advertising_system.ad_manager')
    manager = manager_mod.AdvertisingManager(str(db_path))
    camp_id = manager.create_campaign({'name': 'Camp', 'message_text': 'Hi', 'created_by': 1})
    manager.add_target_group('telegram', 'g1')
    manager.add_target_group('telegram', 'g2')

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    schedule_json = json.dumps({'lunes': ['10:00']})
    cur.execute(
        "INSERT INTO campaign_schedules (campaign_id, schedule_name, frequency, schedule_json, target_platforms, created_date, shop_id) VALUES (?,?,?,?,?, 'now', 1)",
        (camp_id, 'auto', 'daily', schedule_json, 'telegram'),
    )
    schedule_id = cur.lastrowid
    conn.commit()

    cur.execute(
        "SELECT cs.*, c.name, c.message_text, c.media_file_id, c.media_type, c.button1_text, c.button1_url, c.button2_text, c.button2_url FROM campaign_schedules cs JOIN campaigns c ON cs.campaign_id = c.id WHERE cs.id = ?",
        (schedule_id,),
    )
    row = cur.fetchone()
    conn.close()

    sender = AutoSender({'db_path': str(db_path), 'telegram_tokens': ['t']})
    monkeypatch.setattr(sender.scheduler, 'update_next_send', lambda *a, **k: None)

    sender._send_telegram_campaign(camp_id, schedule_id, row)
    assert len(DummyTeleBot.calls) == 2