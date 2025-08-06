import types
import sys
from navigation import nav_system


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
