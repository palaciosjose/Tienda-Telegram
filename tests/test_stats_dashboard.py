import types, sys, pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from navigation import nav_system
import stats_dashboard as sd


def _patch_telebot(monkeypatch):
    class DummyButton:
        def __init__(self, text, callback_data=None):
            self.text = text
            self.callback_data = callback_data

    class DummyMarkup:
        def __init__(self):
            self.keyboard = []

        def add(self, *buttons):
            self.keyboard.append(list(buttons))

    fake = types.SimpleNamespace(
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=DummyMarkup, InlineKeyboardButton=DummyButton
        )
    )
    monkeypatch.setitem(sys.modules, 'telebot', fake)


def test_stats_dashboard_quick_actions(monkeypatch):
    _patch_telebot(monkeypatch)
    nav_system.reset(5)

    monkeypatch.setattr(sd.db, 'get_sales_metrics', lambda sid: {'today':1,'month':2,'total':3})
    monkeypatch.setattr(sd.db, 'get_user_metrics', lambda sid: {'today':4,'month':5,'total':6})

    called = {}

    def fake_send(bot, chat_id, text, markup=None, **kw):
        called['text'] = text
        called['markup'] = markup

    monkeypatch.setattr(sd, 'send_long_message', fake_send)

    sd.show_stats_dashboard(1, 5)

    assert 'Ventas' in called['text'] and 'Usuarios' in called['text']
    actions = nav_system.get_quick_actions(5, 'stats_dashboard_1')
    assert [t for t, _ in actions] == ['📈 Ventas', '👥 Usuarios']
    for text, _ in actions:
        assert not text[0].isalnum()
        assert len(text) <= 15


def test_stats_callbacks(monkeypatch):
    _patch_telebot(monkeypatch)
    nav_system.reset(7)

    called = []

    def fake_send(bot, chat_id, text, markup=None, **kw):
        called.append((text, markup))

    monkeypatch.setattr(sd, 'send_long_message', fake_send)
    monkeypatch.setattr(sd.db, 'get_sales_metrics', lambda sid: {})
    monkeypatch.setattr(sd.db, 'get_user_metrics', lambda sid: {})
    monkeypatch.setattr(sd.db, 'get_sales_timeseries', lambda sid: [{'day':'a','total':1}])
    monkeypatch.setattr(sd.db, 'get_user_timeseries', lambda sid: [{'day':'a','users':2}])

    sd.show_stats_dashboard(1,7)
    assert 'stats_sales' in nav_system._actions and 'stats_users' in nav_system._actions
    nav_system.handle('stats_sales',7,1)
    nav_system.handle('stats_users',7,1)

    texts = [t for t,_ in called]
    assert any('Ventas' in t for t in texts)
    assert any('Usuarios' in t for t in texts)
    # ensure navigation buttons exist
    for _, markup in called:
        buttons = [b.text for row in getattr(markup, 'keyboard', []) for b in row]
        assert '🏠 Inicio' in buttons
        assert '❌ Cancelar' in buttons
