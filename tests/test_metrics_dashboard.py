import types
import pathlib, sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from metrics_dashboard import show_global_metrics


class DummyBot:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.messages.append((chat_id, text, reply_markup))


def test_show_global_metrics_access_denied(monkeypatch):
    import metrics_dashboard

    dummy = DummyBot()
    monkeypatch.setattr(metrics_dashboard, 'bot', dummy)
    monkeypatch.setattr(metrics_dashboard.db, 'get_user_role', lambda uid: 'user')

    show_global_metrics(1, 2)

    assert any('Acceso restringido' in m[1] for m in dummy.messages)


def test_show_global_metrics_content(monkeypatch):
    import metrics_dashboard

    dummy = DummyBot()
    monkeypatch.setattr(metrics_dashboard, 'bot', dummy)
    monkeypatch.setattr(metrics_dashboard.db, 'get_user_role', lambda uid: 'superadmin')
    monkeypatch.setattr(
        metrics_dashboard.db,
        'get_global_metrics',
        lambda: {
            'roi': 10,
            'ranking': [{'name': 'Shop1', 'total': 100}],
            'telethon_active': 1,
            'telethon_total': 2,
        },
    )
    monkeypatch.setattr(
        metrics_dashboard.db,
        'get_alerts',
        lambda limit=5: [{'level': 'ERROR', 'message': 'Algo'}],
    )
    events = []
    monkeypatch.setattr(
        metrics_dashboard.db,
        'log_event',
        lambda level, message, store_id=None: events.append((level, message, store_id)),
    )

    class Markup:
        def __init__(self):
            self.keyboard = []

        def add(self, *btns):
            self.keyboard.append(list(btns))

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

    show_global_metrics(1, 1)

    text = '\n'.join(m[1] for m in dummy.messages)
    assert 'ROI: 10' in text
    assert 'Shop1' in text
    assert 'Telethon: 1/2 activos' in text
    assert 'ERROR: Algo' in text

    markup = dummy.messages[0][2]
    buttons = [btn for row in markup.keyboard for btn in row if btn.callback_data == 'global_metrics']
    texts = [b.text for b in buttons]
    assert texts == ['🔄 Actualizar', '📊 Reportes', '⚠️ Alertas']
    assert events and events[0][0] == 'INFO'
