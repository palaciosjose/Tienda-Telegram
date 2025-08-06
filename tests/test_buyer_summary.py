import sqlite3
from tests.test_categories import setup_dop


def test_get_buyers_summary(monkeypatch, tmp_path):
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/bot")
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    conn = sqlite3.connect(tmp_path / "main.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO purchases (id, username, name_good, amount, price, shop_id) VALUES (1,'u1','P1',1,5,1)"
    )
    cur.execute(
        "INSERT INTO purchases (id, username, name_good, amount, price, shop_id) VALUES (1,'u1','P2',1,10,1)"
    )
    cur.execute(
        "INSERT INTO purchases (id, username, name_good, amount, price, shop_id) VALUES (2,'u2','P2',1,20,1)"
    )
    conn.commit()
    conn.close()

    lines = dop.get_buyers_summary(1)
    assert len(lines) == 2
    line_u1 = next((l for l in lines if 'u1' in l), '')
    assert '15' in line_u1
    assert 'P1' in line_u1 and 'P2' in line_u1
