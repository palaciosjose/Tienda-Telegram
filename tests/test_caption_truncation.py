import importlib, sys, types

class DummyTeleBot:
    def __init__(self, token):
        self.sent = {}
    def send_photo(self, photo=None, caption=None, **kw):
        self.sent['caption'] = caption
    def send_video(self, video=None, caption=None, **kw):
        self.sent['caption'] = caption
    def send_document(self, document=None, caption=None, **kw):
        self.sent['caption'] = caption
    def send_message(self, *a, **k):
        self.sent['text'] = k.get('text')


def test_caption_is_truncated(monkeypatch):
    sys.modules.pop('advertising_system.telegram_multi', None)
    telebot_stub = types.SimpleNamespace(
        TeleBot=DummyTeleBot,
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=lambda *a, **k: None,
            InlineKeyboardButton=lambda *a, **k: None,
        ),
    )
    monkeypatch.setitem(sys.modules, 'telebot', telebot_stub)
    tele_mod = importlib.import_module('advertising_system.telegram_multi')
    bot = tele_mod.TelegramMultiBot(['t'])
    long_text = 'x' * 1050
    ok, _ = bot.send_message('g', long_text, media_file_id='id', media_type='photo')
    assert ok
    assert len(bot.bots[0].sent['caption']) <= 1024
