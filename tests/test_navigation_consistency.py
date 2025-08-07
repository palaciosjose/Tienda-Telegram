import os
import sys

# Ensure project root is on ``sys.path`` for direct module imports.
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import metrics_dashboard as md
import telethon_dashboard as td
from navigation import nav_system
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
    markup = nav_system.create_universal_navigation(1, 'p1', [('🔍 Buscar', 'search')])
    data = markup.to_dict()['inline_keyboard']
    assert [b['text'] for b in data[-1]] == ['🔄 Actualizar', '🏠 Inicio', '❌ Cancelar']
    markup = nav_system.create_universal_navigation(1, 'p2')
    data = markup.to_dict()['inline_keyboard']
    assert [b['text'] for b in data[-1]] == ['⬅️ Atrás', '🔄 Actualizar', '🏠 Inicio', '❌ Cancelar']


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
