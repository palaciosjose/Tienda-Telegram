from tests.test_shop_info import setup_main
import types
import sys
from navigation import nav_system


def test_home_button_calls_main_menu(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    sid = dop.create_shop('S1', admin_id=1)
    dop.set_user_shop(5, sid)

    called = {}

    def fake_menu(cid, username, name):
        called['menu'] = (cid, username, name)

    monkeypatch.setattr(main, 'send_main_menu', fake_menu)
    monkeypatch.setattr(main.bot, 'answer_callback_query', lambda *a, **k: None, raising=False)

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=5, username='u')
            self.message_id = 1
            self.content_type = 'text'
            self.from_user = types.SimpleNamespace(first_name='N')

    cb = types.SimpleNamespace(data='Volver al inicio', message=Msg(), id='1', from_user=types.SimpleNamespace(username='u'))
    main.inline(cb)

    assert called.get('menu') == (5, 'u', 'N')

def test_universal_navigation_buttons(monkeypatch):
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
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=Markup, InlineKeyboardButton=Button
        )
    )
    monkeypatch.setitem(sys.modules, 'telebot', stub)

    markup = nav_system.create_universal_navigation(1, 'test')
    texts = [b.text for b in markup.buttons]
    assert '🏠 Inicio' in texts
    assert '❌ Cancelar' in texts
