import types, sys, pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))


def test_store_dashboard_shows_timeseries(monkeypatch):
    calls = []

    class Bot:
        def send_message(self, chat_id, text=None, reply_markup=None, **kw):
            calls.append(text)

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

    import importlib, adminka
    importlib.reload(adminka)
    monkeypatch.setattr(adminka.db, 'get_store_stats', lambda sid: {'products': 1, 'purchases': 2, 'revenue': 30})
    monkeypatch.setattr(adminka.telethon_manager, 'get_stats', lambda sid: {'active': True, 'sent': 0})
    monkeypatch.setattr(adminka.db, 'get_sales_timeseries', lambda sid, days=7: [{'day':'a','total':1},{'day':'b','total':2}])
    monkeypatch.setattr(adminka.db, 'get_campaign_timeseries', lambda sid, days=7: [{'day':'a','count':0},{'day':'b','count':1}])

    adminka.show_store_dashboard_unified(1, 1, 'Shop')
    text = calls[0]
    assert '💰' in text and '📣' in text
