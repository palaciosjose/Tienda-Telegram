import pathlib, sys, sqlite3

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from business_intelligence import generate_bi_report
import db


def _setup_db():
    con = sqlite3.connect(':memory:')
    cur = con.cursor()
    cur.execute('CREATE TABLE shops (id INTEGER PRIMARY KEY, name TEXT)')
    cur.execute('CREATE TABLE purchases (shop_id INTEGER, price REAL, timestamp TEXT)')
    cur.executemany('INSERT INTO shops (id, name) VALUES (?,?)', [(1, 'Shop1'), (2, 'Shop2')])
    # Shop1 revenue 100
    cur.executemany(
        'INSERT INTO purchases (shop_id, price, timestamp) VALUES (?,?,?)',
        [(1, 50, '2024-01-01'), (1, 50, '2024-01-02'), (2, 30, '2024-01-01'), (2, 20, '2024-01-02')],
    )
    con.commit()
    return con


def test_generate_bi_report_roi_and_ranking(monkeypatch):
    con = _setup_db()
    monkeypatch.setattr(db, 'get_db_connection', lambda: con)
    monkeypatch.setattr(db, 'get_sales_timeseries', lambda store_id=None, days=7: [])

    text = generate_bi_report()

    assert 'ROI: 100' in text
    assert 'ROI: 50' in text

    lines = [l for l in text.splitlines() if l and l[0].isdigit()]
    assert lines[0].startswith('1. Shop1')
    assert lines[1].startswith('2. Shop2')


class DummyBot:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.messages.append((chat_id, text, reply_markup))


def test_show_bi_report_access(monkeypatch):
    import adminka

    dummy = DummyBot()
    monkeypatch.setattr(adminka, 'bot', dummy)
    monkeypatch.setattr(
        adminka.nav_system,
        'create_universal_navigation',
        lambda c, p, quick_actions=None: None,
    )
    monkeypatch.setattr(adminka, 'generate_bi_report', lambda: 'REP')

    events = []
    monkeypatch.setattr(
        adminka.db,
        'log_event',
        lambda level, message, store_id=None: events.append((level, message, store_id)),
    )

    # SuperAdmin access allowed
    monkeypatch.setattr(adminka.db, 'get_user_role', lambda uid: 'superadmin')
    adminka.show_bi_report(1, 1)
    assert any('REP' in m[1] for m in dummy.messages)
    assert events and events[-1][0] == 'INFO'

    # Regular user denied
    dummy.messages.clear()
    events.clear()
    monkeypatch.setattr(adminka.db, 'get_user_role', lambda uid: 'user')
    adminka.show_bi_report(1, 2)
    assert any('Solo SuperAdmin' in m[1] for m in dummy.messages)
    assert events and events[-1][0] == 'WARNING'
