import sqlite3, datetime
from tests.test_categories import setup_dop


def test_toggle_discount_features(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    conf = dop.get_discount_config()
    assert conf['enabled']

    dop.update_discount_config(enabled=False, shop_id=1)
    assert not dop.get_discount_config()['enabled']

    dop.update_discount_config(show_fake_price=False, shop_id=1)
    assert not dop.get_discount_config()['show_fake_price']

    dop.update_discount_config(text='X', multiplier=2.0, shop_id=1)
    conf = dop.get_discount_config()
    assert conf['text'] == 'X'
    assert conf['multiplier'] == 2.0

    conn = sqlite3.connect(tmp_path / "main.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO goods (name, description, format, minimum, price, stored, shop_id) VALUES ('P','d','text',1,100,'x',1)")
    conn.commit()
    conn.close()

    start = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    dop.create_discount(10, start, None, None, 1)
    assert dop.get_active_discount('P', 1) == 10

    dop.update_active_discount_percent(25, shop_id=1)
    assert dop.get_active_discount('P', 1) == 25

