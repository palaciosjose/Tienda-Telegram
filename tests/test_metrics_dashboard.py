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
    monkeypatch.setattr(
        metrics_dashboard.db,
        'get_sales_timeseries',
        lambda store_id=None, days=7: [{'day': 'd1', 'total': 1}, {'day': 'd2', 'total': 3}],
    )
    monkeypatch.setattr(
        metrics_dashboard.db,
        'get_campaign_timeseries',
        lambda store_id=None, days=7: [{'day': 'd1', 'count': 0}, {'day': 'd2', 'count': 2}],
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
    assert '💹' in text
    assert '📣' in text

    markup = dummy.messages[0][2]
    buttons = [(btn.text, btn.callback_data) for row in markup.keyboard for btn in row]
    assert ('📊 Reportes', 'global_metrics') in buttons
    assert ('⚠️ Alertas', 'global_alerts') in buttons
    assert ('🔄 Actualizar', 'GLOBAL_REFRESH') in buttons
    assert events and events[0][0] == 'INFO'


def test_db_get_store_stats(tmp_path, monkeypatch):
    import sqlite3
    import files
    import db

    db_path = tmp_path / "main.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(files, "main_db", str(db_path))
    db.close_connection()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE goods (shop_id INTEGER)")
    cur.executemany("INSERT INTO goods (shop_id) VALUES (?)", [(1,), (1,), (2,)])
    cur.execute("CREATE TABLE purchases (shop_id INTEGER, price INTEGER)")
    cur.executemany(
        "INSERT INTO purchases (shop_id, price) VALUES (?,?)",
        [(1, 10), (1, 20), (2, 5)],
    )
    conn.commit()
    conn.close()

    assert db.get_store_stats(1) == {"products": 2, "purchases": 2, "revenue": 30}
    assert db.get_store_stats(2) == {"products": 1, "purchases": 1, "revenue": 5}


def test_db_global_metrics_and_topics(tmp_path, monkeypatch):
    import sqlite3
    import files
    import db

    db_path = tmp_path / "main.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(files, "main_db", str(db_path))
    db.close_connection()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("CREATE TABLE purchases (shop_id INTEGER, price INTEGER)")
    cur.executemany(
        "INSERT INTO purchases (shop_id, price) VALUES (?,?)",
        [(1, 10), (1, 20), (2, 5)],
    )
    cur.execute("CREATE TABLE shops (id INTEGER PRIMARY KEY, name TEXT)")
    cur.executemany("INSERT INTO shops (id, name) VALUES (?,?)", [(1, 'A'), (2, 'B')])
    cur.execute("CREATE TABLE platform_config (platform TEXT, is_active INTEGER)")
    cur.executemany(
        "INSERT INTO platform_config (platform, is_active) VALUES ('telethon', ?)",
        [(1,), (0,)],
    )
    conn.commit()
    conn.close()

    metrics = db.get_global_metrics()
    assert metrics["revenue"] == 35
    assert metrics["roi"] == 35
    assert metrics["telethon_active"] == 1
    assert metrics["telethon_total"] == 2
    assert metrics["ranking"][0]["name"] == "A"

    topics = [
        {"group_id": "g1", "group_name": "G1", "topic_id": 1, "topic_name": "T1"},
        {"group_id": "g2", "group_name": "G2", "topic_id": 2, "topic_name": "T2"},
    ]
    db.save_detected_topics(1, topics)
    assert db.get_store_topics(1) == topics
