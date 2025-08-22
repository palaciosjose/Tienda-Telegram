import os
import sys

# Ensure project root is on ``sys.path`` for direct module imports.
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import metrics_dashboard as md
import telethon_dashboard as td
from navigation import nav_system
from tests.test_shop_info import setup_main
import types


def _patch_telebot(monkeypatch):
    """Provide a minimal telebot replacement for markup creation."""
    class DummyButton:
        def __init__(self, text, callback_data):
            self.text = text
            self.callback_data = callback_data

    class DummyMarkup:
        def __init__(self):
            self.keyboard = []

        def add(self, *buttons):
            self.keyboard.append(list(buttons))

        def to_dict(self):
            return {
                'inline_keyboard': [
                    [{'text': b.text, 'callback_data': b.callback_data} for b in row]
                    for row in self.keyboard
                ]
            }

    fake = types.SimpleNamespace(
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=DummyMarkup, InlineKeyboardButton=DummyButton
        )
    )
    monkeypatch.setitem(sys.modules, 'telebot', fake)


def test_universal_navigation_structure(monkeypatch):
    _patch_telebot(monkeypatch)
    nav_system.reset(1)
    actions = [('A', 'a'), ('B', 'b'), ('C', 'c'), ('D', 'd')]
    markup = nav_system.create_universal_navigation(1, 'p1', actions)
    data = markup.to_dict()['inline_keyboard']
    assert len(data[0]) == 3  # first three quick actions
    assert len(data[1]) == 1  # remaining quick action
    assert [b['text'] for b in data[-1]] == ['🔄 Actualizar', '🏠 Inicio', '❌ Cancelar']
    assert all(len(row) <= 3 for row in data)

    markup = nav_system.create_universal_navigation(1, 'p2')
    data = markup.to_dict()['inline_keyboard']
    assert [b['text'] for b in data[-2]] == ['⬅️ Atrás', '🔄 Actualizar', '🏠 Inicio']
    assert [b['text'] for b in data[-1]] == ['❌ Cancelar']
    assert all(len(row) <= 3 for row in data)


def test_dashboard_quick_action_labels(monkeypatch):
    _patch_telebot(monkeypatch)
    nav_system.reset(10)
    # --- metrics dashboard ---
    monkeypatch.setattr(md.db, 'get_user_role', lambda uid: 'superadmin')
    monkeypatch.setattr(md.db, 'get_global_metrics', lambda: {})
    monkeypatch.setattr(md.db, 'get_alerts', lambda: [])
    monkeypatch.setattr(md.db, 'get_sales_timeseries', lambda: [])
    monkeypatch.setattr(md.db, 'get_campaign_timeseries', lambda: [])
    monkeypatch.setattr(md.db, 'log_event', lambda *a, **k: None)
    monkeypatch.setattr(md, 'send_long_message', lambda *a, **k: None)
    md.show_global_metrics(10, 10)
    metrics_actions = nav_system.get_quick_actions(10, 'global_metrics')
    assert [t for t, _ in metrics_actions] == ['📊 Reportes', '⚠️ Alertas']
    for text, _ in metrics_actions:
        assert not text[0].isalnum()
        assert len(text) <= 15

    # --- telethon dashboard ---
    nav_system.reset(20)
    monkeypatch.setattr(td.telethon_manager, 'get_stats', lambda store_id: {'active': True, 'sent': 0})
    monkeypatch.setattr(td, 'send_long_message', lambda *a, **k: None)
    td.show_telethon_dashboard(20, 5)
    telethon_actions = nav_system.get_quick_actions(20, 'telethon_dashboard_5')
    assert [t for t, _ in telethon_actions] == ['🧵 Topics', '✉️ Prueba', '♻️ Reiniciar']
    for text, _ in telethon_actions:
        assert not text[0].isalnum()
        assert len(text) <= 15


def test_quick_actions_prioritized(monkeypatch):
    _patch_telebot(monkeypatch)
    nav_system.reset(99)
    nav_system.register('A', lambda c, s: None)
    nav_system.register('B', lambda c, s: None)
    nav_system.create_universal_navigation(99, 'p', [('🔵 A', 'A'), ('🟢 B', 'B')])
    nav_system.handle('B', 99, 0)
    nav_system.handle('B', 99, 0)
    nav_system.handle('A', 99, 0)
    actions = nav_system.get_quick_actions(99, 'p')
    assert [cb for _, cb in actions] == ['B', 'A']


def test_back_and_refresh_callbacks(monkeypatch):
    _patch_telebot(monkeypatch)
    nav_system.reset(50)
    called = []
    nav_system.register('page1', lambda c, u: called.append('page1'))
    nav_system.register('page2', lambda c, u: called.append('page2'))
    nav_system.create_universal_navigation(50, 'page1')
    nav_system.create_universal_navigation(50, 'page2')
    nav_system.handle(nav_system.current(50), 50, 0)
    assert called[-1] == 'page2'
    nav_system.handle(nav_system.back(50), 50, 0)
    assert called[-1] == 'page1'


def test_inline_global_callbacks(monkeypatch, tmp_path):
    _patch_telebot(monkeypatch)
    _, main, _, _ = setup_main(monkeypatch, tmp_path)
    monkeypatch.setattr(main.dop, 'get_goods', lambda *a, **k: [])
    called = []

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=1)
            self.message_id = 1
            self.content_type = 'text'
            self.from_user = types.SimpleNamespace(id=0)

    cb = types.SimpleNamespace(data='GLOBAL_CANCEL', message=Msg(), id='1', from_user=types.SimpleNamespace(id=0))

    monkeypatch.setattr(main.nav_system, 'reset', lambda cid: called.append(('reset', cid)))
    monkeypatch.setattr(main, 'show_shop_selection', lambda cid, msg=None: called.append(('show', cid)))
    main.inline(cb)
    assert called == [('reset', 1), ('show', 1)]

    called.clear()
    monkeypatch.setattr(main.nav_system, 'back', lambda cid: called.append(('back', cid)) or 'prev')
    monkeypatch.setattr(main.nav_system, 'handle', lambda name, cid, uid: called.append(('handle', name, cid, uid)))
    cb.data = 'GLOBAL_BACK'
    main.inline(cb)
    assert ('back', 1) in called and ('handle', 'prev', 1, 0) in called

    called.clear()
    monkeypatch.setattr(main.nav_system, 'current', lambda cid: called.append(('current', cid)) or 'cur')
    monkeypatch.setattr(main.nav_system, 'handle', lambda name, cid, uid: called.append(('handle', name, cid, uid)))
    cb.data = 'GLOBAL_REFRESH'
    main.inline(cb)
    assert ('current', 1) in called and ('handle', 'cur', 1, 0) in called


def test_admin_menus_have_standard_buttons(monkeypatch):
    _patch_telebot(monkeypatch)
    import adminka

    markups = []

    def fake_send(bot, chat_id, text, markup=None, **kwargs):
        markups.append(markup)

    monkeypatch.setattr(adminka, 'send_long_message', fake_send)
    monkeypatch.setattr(adminka.dop, 'get_shop_id', lambda cid: 1)
    monkeypatch.setattr(
        adminka.dop,
        'get_discount_config',
        lambda sid: {
            'enabled': False,
            'show_fake_price': False,
            'text': 't',
            'multiplier': 1,
        },
    )
    monkeypatch.setattr(adminka.dop, 'get_campaign_limit', lambda sid: 0)
    monkeypatch.setattr(adminka.advertising, 'get_all_campaigns', lambda: [])

    class DummyScheduler:
        def __init__(self, *a, **k):
            pass

        def get_pending_sends(self):
            return []

    monkeypatch.setattr(adminka, 'CampaignScheduler', DummyScheduler)
    monkeypatch.setattr(adminka.telethon_manager, 'get_stats', lambda sid: {'active': False})
    monkeypatch.setattr(adminka.db, 'get_store_stats', lambda sid: {})
    monkeypatch.setattr(adminka.db, 'get_sales_timeseries', lambda sid, days=7: [])
    monkeypatch.setattr(adminka.db, 'get_campaign_timeseries', lambda sid, days=7: [])
    monkeypatch.setattr(adminka.db, 'get_store_topics', lambda sid: [])
    monkeypatch.setattr(adminka.db, 'get_db_connection', lambda: (_ for _ in ()).throw(Exception()))

    menus = [
        lambda: adminka.show_main_admin_menu(1),
        lambda: adminka.show_store_dashboard_unified(1, 1, 'Shop'),
        lambda: adminka.show_marketing_unified(1, 1),
        lambda: adminka.manage_discounts(1, 1),
        lambda: adminka.show_other_settings(1, 1),
    ]

    for menu in menus:
        markups.clear()
        nav_system.reset(1)
        menu()
        markup = markups[-1]
        texts = [btn.text for row in markup.keyboard for btn in row]
        assert '🏠 Inicio' in texts
        assert '🔄 Actualizar' in texts
        assert '❌ Cancelar' in texts


def test_home_button_resets_navigation(monkeypatch, tmp_path):
    dop, main, _, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop('S1', admin_id=1)
    dop.set_user_shop(5, sid)

    called = {}

    def fake_show(cid, message=None):
        called['select'] = (cid, message)

    monkeypatch.setattr(main, 'show_shop_selection', fake_show)
    reset_called = []
    monkeypatch.setattr(main.nav_system, 'reset', lambda cid: reset_called.append(cid))
    monkeypatch.setattr(main.bot, 'answer_callback_query', lambda *a, **k: None, raising=False)

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=5, username='u')
            self.message_id = 1
            self.content_type = 'text'
            self.from_user = types.SimpleNamespace(first_name='N')

    cb = types.SimpleNamespace(data='Volver al inicio', message=Msg(), id='1', from_user=types.SimpleNamespace(username='u'))
    main.inline(cb)

    assert called.get('select')[0] == 5
    assert reset_called == [5]
