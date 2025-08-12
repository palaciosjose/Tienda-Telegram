import importlib
import sqlite3
import sys
import types
import json
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Minimal database schema copied from advertising tests
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
    cur.execute("CREATE TABLE goods (name TEXT, description TEXT, price REAL, media_file_id TEXT, media_type TEXT, shop_id INTEGER DEFAULT 1)")
    cur.execute(CREATE_SCHEDULES_TABLE)
    conn.commit()
    conn.close()


class DummyTeleBot:
    def __init__(self, token):
        pass

    def send_message(self, *a, **kw):
        DummyTeleBot.calls.append(kw.get('message_thread_id'))

DummyTeleBot.calls = []

telebot_stub = types.SimpleNamespace(
    TeleBot=DummyTeleBot,
    types=types.SimpleNamespace(
        InlineKeyboardMarkup=lambda *a, **k: None,
        InlineKeyboardButton=lambda *a, **k: None,
    ),
)


class DummyTeleBotWithGroup:
    def __init__(self, token):
        pass

    def send_message(self, chat_id, text=None, **kw):
        DummyTeleBotWithGroup.calls.append((chat_id, kw.get('message_thread_id')))

DummyTeleBotWithGroup.calls = []

telebot_stub_with_group = types.SimpleNamespace(
    TeleBot=DummyTeleBotWithGroup,
    types=types.SimpleNamespace(
        InlineKeyboardMarkup=lambda *a, **k: None,
        InlineKeyboardButton=lambda *a, **k: None,
    ),
)


def test_send_campaign_to_group_with_topic(tmp_path, monkeypatch):
    DummyTeleBot.calls.clear()
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub)
    sys.modules.pop('advertising_system.telegram_multi', None)
    sys.modules.pop('advertising_system.ad_manager', None)
    ad_mod = importlib.import_module('advertising_system.ad_manager')
    AdvertisingManager = ad_mod.AdvertisingManager

    db_path = tmp_path / 'ads.db'
    init_ads_db(db_path)
    manager = AdvertisingManager(str(db_path))
    camp_id = manager.create_campaign({'name': 'Camp', 'message_text': 'Hi', 'created_by': 1})
    monkeypatch.setenv('TELEGRAM_TOKEN', 't')

    ok, msg = manager.send_campaign_to_group(camp_id, '111', topic_id=42)
    assert ok
    assert DummyTeleBot.calls == [42]

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT platform, status FROM send_logs')
    rows = cur.fetchall()
    conn.close()
    assert rows == [('telegram', 'sent')]


def test_auto_sender_topic_groups(tmp_path, monkeypatch):
    DummyTeleBot.calls.clear()
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub)
    sys.modules.pop('advertising_system.telegram_multi', None)
    sys.modules.pop('advertising_system.auto_sender', None)
    auto_mod = importlib.import_module('advertising_system.auto_sender')
    AutoSender = auto_mod.AutoSender

    db_path = tmp_path / 'ads.db'
    init_ads_db(db_path)
    manager_mod = importlib.import_module('advertising_system.ad_manager')
    manager = manager_mod.AdvertisingManager(str(db_path))
    camp_id = manager.create_campaign({'name': 'Camp', 'message_text': 'Hi', 'created_by': 1})
    manager.add_target_group('telegram', 'g1', topic_id=1)
    manager.add_target_group('telegram', 'g2', topic_id=2)
    manager.schedule_campaign(camp_id, ['lunes'], ['10:00'])

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT id FROM campaign_schedules')
    schedule_id = cur.fetchone()[0]
    cur.execute(
        "SELECT cs.*, c.name, c.message_text, c.media_file_id, c.media_type, c.button1_text, c.button1_url, c.button2_text, c.button2_url FROM campaign_schedules cs JOIN campaigns c ON cs.campaign_id = c.id WHERE cs.id = ?",
        (schedule_id,),
    )
    row = cur.fetchone()
    conn.close()

    sender = AutoSender({'db_path': str(db_path), 'telegram_tokens': ['t']})
    monkeypatch.setattr(sender.scheduler, 'update_next_send', lambda *a, **k: None)

    sender._send_telegram_campaign(camp_id, schedule_id, row)
    assert DummyTeleBot.calls == [1, 2]


def test_auto_sender_respects_group_ids(tmp_path, monkeypatch):
    DummyTeleBotWithGroup.calls.clear()
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub_with_group)
    sys.modules.pop('advertising_system.telegram_multi', None)
    sys.modules.pop('advertising_system.auto_sender', None)
    auto_mod = importlib.import_module('advertising_system.auto_sender')
    AutoSender = auto_mod.AutoSender

    db_path = tmp_path / 'ads.db'
    init_ads_db(db_path)
    manager_mod = importlib.import_module('advertising_system.ad_manager')
    manager = manager_mod.AdvertisingManager(str(db_path))
    camp_id = manager.create_campaign({'name': 'Camp', 'message_text': 'Hi', 'created_by': 1})
    manager.add_target_group('telegram', 'g1', topic_id=1)
    manager.add_target_group('telegram', 'g2', topic_id=2)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT id FROM target_groups WHERE group_id = ?', ('g2',))
    g2_id = cur.fetchone()[0]
    schedule_json = json.dumps({'lunes': ['10:00']})
    cur.execute(
        "INSERT INTO campaign_schedules (campaign_id, schedule_name, frequency, schedule_json, target_platforms, created_date, shop_id, group_ids) VALUES (?,?,?,?,?, 'now', 1, ?)",
        (camp_id, 'auto', 'daily', schedule_json, 'telegram', str(g2_id)),
    )
    schedule_id = cur.lastrowid
    cur.execute(
        "SELECT cs.*, c.name, c.message_text, c.media_file_id, c.media_type, c.button1_text, c.button1_url, c.button2_text, c.button2_url FROM campaign_schedules cs JOIN campaigns c ON cs.campaign_id = c.id WHERE cs.id = ?",
        (schedule_id,),
    )
    row = cur.fetchone()
    conn.close()

    sender = AutoSender({'db_path': str(db_path), 'telegram_tokens': ['t']})
    monkeypatch.setattr(sender.scheduler, 'update_next_send', lambda *a, **k: None)

    sender._send_telegram_campaign(camp_id, schedule_id, row)
    assert DummyTeleBotWithGroup.calls == [('g2', 2)]


def test_dashboard_has_telethon_button(monkeypatch, tmp_path):
    calls = []

    class Bot:
        def send_message(self, chat_id, text=None, reply_markup=None, **kw):
            calls.append(reply_markup)

    class Markup:
        def __init__(self):
            self.buttons = []

        def add(self, *btns):
            self.buttons.extend(btns)

    class Button:
        def __init__(self, text, callback_data=None, url=None):
            self.text = text
            self.callback_data = callback_data
            self.url = url

    telebot_stub_local = types.SimpleNamespace(
        TeleBot=lambda *a, **k: Bot(),
        types=types.SimpleNamespace(InlineKeyboardMarkup=Markup, InlineKeyboardButton=Button),
    )
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub_local)
    bot = telebot_stub_local.TeleBot()
    monkeypatch.setitem(sys.modules, 'bot_instance', types.SimpleNamespace(bot=bot))

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import files
    monkeypatch.setattr(files, 'main_db', str(tmp_path / 'main.db'))
    os.makedirs('data/db', exist_ok=True)
    open('data/db/main_data.db', 'w').close()

    import importlib, db, adminka
    importlib.reload(adminka)
    sid = 1
    adminka.show_store_dashboard_unified(1, sid, 'S1')
    btn_texts = [b.text for b in calls[0].buttons]
    assert any('Telethon' in t for t in btn_texts)


def test_show_telethon_dashboard_buttons(monkeypatch):
    calls = []

    class Bot:
        def send_message(self, chat_id, text=None, reply_markup=None, **kw):
            calls.append(reply_markup)

    class Markup:
        def __init__(self):
            self.buttons = []

        def add(self, *btns):
            self.buttons.extend(btns)

    class Button:
        def __init__(self, text, callback_data=None):
            self.text = text
            self.callback_data = callback_data

    telebot_stub = types.SimpleNamespace(
        TeleBot=lambda *a, **k: Bot(),
        types=types.SimpleNamespace(InlineKeyboardMarkup=Markup, InlineKeyboardButton=Button),
    )
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub)
    bot = telebot_stub.TeleBot()
    monkeypatch.setitem(sys.modules, 'bot_instance', types.SimpleNamespace(bot=bot))

    import importlib, telethon_dashboard
    importlib.reload(telethon_dashboard)
    monkeypatch.setattr(telethon_dashboard.telethon_manager, 'get_stats', lambda s: {'active': True, 'sent': 0})
    monkeypatch.setattr(telethon_dashboard.db, 'get_store_topics', lambda sid: [])

    telethon_dashboard.show_telethon_dashboard(1, 5)
    markup = calls[0]
    cb_data = {b.callback_data for b in markup.buttons}
    assert f'telethon_detect_5' in cb_data
    assert f'telethon_test_5' in cb_data
    assert f'telethon_restart_5' in cb_data


def test_streaming_manager_routes_telethon_actions(monkeypatch):
    actions = []

    import telethon_manager
    monkeypatch.setattr(telethon_manager, 'detect_topics', lambda sid: actions.append(('detect', sid)))
    monkeypatch.setattr(telethon_manager, 'test_send', lambda sid: actions.append(('test', sid)))

    import telethon_dashboard
    monkeypatch.setattr(
        telethon_dashboard,
        'show_telethon_dashboard',
        lambda chat_id, sid: actions.append(('dash', chat_id, sid)),
    )

    monkeypatch.setitem(sys.modules, 'bot_instance', types.SimpleNamespace(bot=None))
    from streaming_manager_bot import StreamingManagerBot

    class Bot:
        def send_message(self, chat_id, text, **kw):
            actions.append(('msg', chat_id, text))

    monkeypatch.setattr(telethon_manager, 'restart_daemon', lambda sid: actions.append(('restart', sid)))

    sm = StreamingManagerBot(Bot())
    sm.route_callback('telethon_dashboard_3', 9)
    sm.route_callback('telethon_detect_3', 9)
    sm.route_callback('telethon_test_3', 9)
    sm.route_callback('telethon_restart_3', 9)

    assert ('dash', 9, 3) in actions
    assert ('detect', 3) in actions
    assert ('test', 3) in actions
    assert ('restart', 3) in actions


def test_telethon_wizard_missing_credentials(monkeypatch, tmp_path):
    messages = []

    class Bot:
        def send_message(self, chat_id, text, **kw):
            messages.append(text)

    class Markup:
        def add(self, *a, **k):
            pass

    telebot_stub = types.SimpleNamespace(
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=Markup,
            InlineKeyboardButton=lambda *a, **k: None,
        )
    )
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub)
    dummy_bot = Bot()
    monkeypatch.setitem(sys.modules, 'bot_instance', types.SimpleNamespace(bot=dummy_bot))

    import importlib, telethon_config
    importlib.reload(telethon_config)

    monkeypatch.setattr(telethon_config.files, 'sost_bd', str(tmp_path / 'sost.bd'))
    monkeypatch.setattr(telethon_config.db, 'get_global_telethon_status', lambda: {})

    telethon_config.start_telethon_wizard(1, 2)
    assert any('credenciales' in m.lower() for m in messages)


def test_telethon_wizard_activation(monkeypatch, tmp_path):
    messages = []

    class Bot:
        def send_message(self, chat_id, text, **kw):
            messages.append(text)

    class Markup:
        def add(self, *a, **k):
            pass

    telebot_stub = types.SimpleNamespace(
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=Markup,
            InlineKeyboardButton=lambda *a, **k: None,
        )
    )
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub)
    dummy_bot = Bot()
    monkeypatch.setitem(sys.modules, 'bot_instance', types.SimpleNamespace(bot=dummy_bot))

    import importlib, telethon_config
    importlib.reload(telethon_config)

    monkeypatch.setattr(telethon_config.files, 'sost_bd', str(tmp_path / 'sost.bd'))
    monkeypatch.setattr(
        telethon_config.db,
        'get_global_telethon_status',
        lambda: {'api_id': '1', 'api_hash': '2'},
    )

    actions = []
    monkeypatch.setattr(
        telethon_config.telethon_manager,
        'detect_topics',
        lambda sid: actions.append(('detect', sid)),
    )
    monkeypatch.setattr(
        telethon_config.telethon_manager,
        'test_send',
        lambda sid: actions.append(('test', sid)),
    )
    monkeypatch.setattr(
        telethon_config.telethon_manager,
        'restart_daemon',
        lambda sid: actions.append(('activate', sid)),
    )

    telethon_config.start_telethon_wizard(1, 7)
    telethon_config.start_telethon_wizard(1, 7)
    telethon_config.start_telethon_wizard(1, 7)
    telethon_config.start_telethon_wizard(1, 7)

    assert actions == [('detect', 7), ('test', 7), ('activate', 7)]
    import shelve

    with shelve.open(telethon_config.files.sost_bd) as bd:
        assert '1_telethon_step' not in bd
