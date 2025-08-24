import types
import telethon_config

def test_show_global_telethon_config(monkeypatch):
    calls = []

    def fake_send(bot, chat_id, text, markup=None, parse_mode=None):
        calls.append((text, markup))

    monkeypatch.setattr(telethon_config, 'send_long_message', fake_send)
    monkeypatch.setattr(telethon_config.db, 'get_global_telethon_status', lambda: {'b': '1', 'a': '2'})

    class Markup:
        def __init__(self):
            self.buttons = []
        def add(self, *btns):
            self.buttons.extend(btns)

    class Button:
        def __init__(self, text, callback_data=None):
            self.text = text
            self.callback_data = callback_data

    def create_nav(chat_id, key, actions):
        markup = Markup()
        for text, cb in actions:
            markup.add(Button(text, cb))
        return markup

    monkeypatch.setattr(telethon_config.nav_system, 'create_universal_navigation', create_nav)
    telethon_config.show_global_telethon_config(1, 1)

    text, markup = calls[0]
    lines = text.split('\n')
    assert lines[1] == 'a: 2'
    assert lines[2] == 'b: 1'
    callbacks = {b.callback_data for b in markup.buttons}
    assert 'global_restart_daemons' in callbacks
    assert 'global_generate_report' in callbacks
