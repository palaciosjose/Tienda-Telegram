import types, sys, pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))


def test_shop_dashboard_metrics_and_buttons(monkeypatch):
    calls = []

    # Stub telebot and bot instance
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
        TeleBot=lambda *a, **k: object(),
        types=types.SimpleNamespace(InlineKeyboardMarkup=Markup, InlineKeyboardButton=Button),
    )
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub)
    monkeypatch.setitem(sys.modules, 'bot_instance', types.SimpleNamespace(bot=None))

    import importlib, adminka
    importlib.reload(adminka)

    def fake_send(bot, chat_id, text, markup=None, parse_mode=None, **kw):
        calls.append((text, markup))
    monkeypatch.setattr(adminka, 'send_long_message', fake_send)

    monkeypatch.setattr(adminka.db, 'get_store_stats', lambda sid: {'products': 1, 'purchases': 2, 'revenue': 10})
    monkeypatch.setattr(adminka.telethon_manager, 'get_stats', lambda sid: {'active': True, 'sent': 1})
    monkeypatch.setattr(adminka.db, 'get_sales_timeseries', lambda sid: [])
    monkeypatch.setattr(adminka.db, 'get_campaign_timeseries', lambda sid: [])
    monkeypatch.setattr(adminka.db, 'get_store_topics', lambda sid: [1, 2])

    class Cursor:
        def execute(self, q, params=()):
            if 'campaigns' in q:
                self.res = [(3,)]
            elif 'telethon_daemon_status' in q:
                self.res = [('running',)]
            else:
                self.res = [(0,)]
        def fetchone(self):
            return self.res[0]
    class Conn:
        def cursor(self):
            return Cursor()
    monkeypatch.setattr(adminka.db, 'get_db_connection', lambda: Conn())

    adminka.show_store_dashboard_unified(1, 1, 'Shop')
    text, _ = calls[0]
    assert 'Topics' in text and 'Campañas' in text and 'Daemon' in text

    from navigation import nav_system
    quick = nav_system.get_quick_actions(1, 'store_dashboard_1')
    labels = [t for t, _ in quick]
    assert '📢 Marketing' in labels and '🤖 Telethon' in labels
    assert '🧾 Reportes' in labels and '⚙️ Config' in labels
