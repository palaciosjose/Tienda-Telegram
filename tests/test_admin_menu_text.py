from tests.test_shop_info import setup_main
import types
import sys
from navigation import nav_system


def test_admin_menu_text_dispatch(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])

    called = {}

    def fake_in_adminka(chat_id, text, username, name):
        called['args'] = (chat_id, text, username, name)

    monkeypatch.setattr(main.adminka, 'in_adminka', fake_in_adminka)

    class Msg:
        def __init__(self, text):
            self.text = text
            self.chat = types.SimpleNamespace(id=1, username='admin')
            self.from_user = types.SimpleNamespace(first_name='Admin')
            self.content_type = 'text'

    main.message_send(Msg('/adm'))
    calls.clear()
    called.clear()

    main.message_send(Msg('📦 Surtido'))

    assert called.get('args') == (1, '📦 Surtido', 'admin', 'Admin')


def test_navigation_buttons_present(monkeypatch):
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

    actions = [('B', 'b')]
    markup = nav_system.create_universal_navigation(1, 'admin_menu', actions)
    texts = [b.text for b in markup.buttons]
    assert 'B' in texts
    assert '🏠 Inicio' in texts
    assert '❌ Cancelar' in texts
    assert nav_system.get_quick_actions(1) == actions
