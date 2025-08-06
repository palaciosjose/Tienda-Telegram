import os, sqlite3, sys, pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import db, files


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / 'main.db'
    monkeypatch.setattr(files, 'main_db', str(db_path))
    os.makedirs(tmp_path, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('CREATE TABLE purchases (id INTEGER, price INTEGER, timestamp TEXT, shop_id INTEGER)')
    cur.execute('CREATE TABLE send_logs (id INTEGER, sent_date TEXT, shop_id INTEGER)')
    conn.commit()
    return conn


def test_timeseries_functions(tmp_path, monkeypatch):
    conn = _setup(tmp_path, monkeypatch)
    cur = conn.cursor()
    cur.executemany('INSERT INTO purchases VALUES (?,?,?,?)', [
        (1, 10, '2024-01-01T00:00:00', 1),
        (2, 20, '2024-01-02T00:00:00', 1),
    ])
    cur.executemany('INSERT INTO send_logs VALUES (?,?,?)', [
        (1, '2024-01-01', 1),
        (2, '2024-01-02', 1),
        (3, '2024-01-02', 1),
    ])
    conn.commit()
    conn.close()

    db.close_connection()
    sales = db.get_sales_timeseries(1, 7)
    camps = db.get_campaign_timeseries(1, 7)
    assert sales[-1]['total'] == 20
    assert camps[-1]['count'] == 2
