import types, sys, shelve
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import adminka, files, dop
from navigation import nav_system

def _stub_telebot(monkeypatch):
    class Markup:
        def __init__(self):
            self.buttons = []
        def add(self, *btns):
            self.buttons.extend(btns)
    class Button:
        def __init__(self, text, callback_data=None):
            self.text = text
            self.callback_data = callback_data
    stub = types.SimpleNamespace(
        types=types.SimpleNamespace(InlineKeyboardMarkup=Markup, InlineKeyboardButton=Button)
    )
    monkeypatch.setitem(sys.modules, 'telebot', stub)


def test_configure_responses_actions(monkeypatch, tmp_path):
    _stub_telebot(monkeypatch)
    nav_system.reset(1)
    monkeypatch.setattr(files, 'bot_message_bd', str(tmp_path/'msg.db'))
    monkeypatch.setattr(files, 'sost_bd', str(tmp_path/'state.db'))
    monkeypatch.setattr(adminka, 'send_long_message', lambda *a, **k: None)
    # Preload start message so preview action appears
    with shelve.open(files.bot_message_bd) as bd:
        bd['start'] = 'hi'
    adminka.configure_responses(1, 1)
    actions = nav_system.get_quick_actions(1, 'configure_responses')
    callbacks = [c for _, c in actions]
    assert 'response_edit_start' in callbacks
    assert 'response_preview_start' in callbacks


def test_response_edit_flow(monkeypatch, tmp_path):
    _stub_telebot(monkeypatch)
    nav_system.reset(2)
    monkeypatch.setattr(files, 'bot_message_bd', str(tmp_path/'msg.db'))
    monkeypatch.setattr(files, 'sost_bd', str(tmp_path/'state.db'))
    monkeypatch.setattr(dop, 'get_shop_id', lambda cid: 1)
    sent = []
    def fake_send(bot, chat_id, text, markup=None, parse_mode=None):
        sent.append(text)
    monkeypatch.setattr(adminka, 'send_long_message', fake_send)
    adminka.response_edit_start(2, 1)
    adminka.text_analytics('nuevo', 2)
    with shelve.open(files.bot_message_bd) as bd:
        assert bd['start'] == 'nuevo'
    # After saving, configure_responses should be shown
    assert any('Respuestas' in t for t in sent)
