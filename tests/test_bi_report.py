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
