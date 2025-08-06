import sqlite3
from datetime import datetime, timedelta
from tests.test_categories import setup_dop


def test_new_buy_improved_sets_expiration(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    conn = sqlite3.connect(tmp_path / "main.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO goods (name, description, format, minimum, price, stored, duration_days, shop_id) VALUES ('P','d','text',1,5,'x',7,1)"
    )
    conn.commit()
    conn.close()

    assert dop.new_buy_improved(1, 'user', 'P', 1, 5, 'paypal', 'pid', 1)

    conn = sqlite3.connect(tmp_path / "main.db")
    cur = conn.cursor()
    cur.execute("SELECT expires_at FROM purchases WHERE id=1 AND name_good='P'")
    exp = cur.fetchone()[0]
    conn.close()

    assert exp is not None
    dt = datetime.fromisoformat(exp)
    assert dt - datetime.now() > timedelta(days=6)
