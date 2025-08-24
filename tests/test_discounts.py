import sqlite3, datetime
from tests.test_categories import setup_dop


def test_discount_creation_and_application(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    conn = sqlite3.connect(tmp_path / "main.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO categories (id,name,shop_id) VALUES (1,'Cat',1)")
    cur.execute(
        "INSERT INTO goods (name, description, format, minimum, price, stored, category_id, shop_id) "
        "VALUES ('Prod','d','text',1,100,'x',1,1)"
    )
    conn.commit()
    conn.close()

    start = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    dop.create_discount(20, start, None, 1, 1)

    assert dop.get_active_discount('Prod', 1) == 20
    assert dop.order_sum('Prod', 2, 1) == 160

    desc = dop.get_description('Prod', 1)
    assert '80 USD' in desc
