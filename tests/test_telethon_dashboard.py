import types
import telethon_dashboard

def test_telethon_dashboard_lists_topics_and_alerts(monkeypatch):
    messages = []

    def fake_send(bot, chat_id, text, markup=None, parse_mode=None):
        messages.append(text)

    monkeypatch.setattr(telethon_dashboard, 'send_long_message', fake_send)
    monkeypatch.setattr(telethon_dashboard.nav_system, 'create_universal_navigation', lambda *a, **k: None)
    monkeypatch.setattr(telethon_dashboard.telethon_manager, 'get_stats', lambda s: {'daemon': 'ok', 'last_activity': 'hoy', 'api': True, 'topics': 1, 'last_send': 'ayer'})
    monkeypatch.setattr(telethon_dashboard.db, 'get_daily_campaign_counts', lambda sid: {'current': 2, 'max': 3})
    monkeypatch.setattr(telethon_dashboard.db, 'get_alerts', lambda limit=3: [{'message': 'Algo'}])
    monkeypatch.setattr(telethon_dashboard.db, 'get_store_topics', lambda sid: [{'group_id': 'g', 'topic_id': 1, 'group_name': 'G'}])

    class DummyCursor:
        def execute(self, *a, **k):
            pass
        def fetchone(self):
            return [0]

    class DummyConn:
        def cursor(self):
            return DummyCursor()

    monkeypatch.setattr(telethon_dashboard.db, 'get_db_connection', lambda: DummyConn())

    telethon_dashboard.show_telethon_dashboard(1, 5)
    text = messages[0]
    assert 'Campañas hoy: 2' in text
    assert '⚡ 2/3' in text
    assert 'G (1) - 0/0' in text
    assert '⚠️ Algo' in text
