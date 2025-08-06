import sqlite3
from tests.test_categories import setup_dop


def test_product_media_filtered_by_shop(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    conn = sqlite3.connect(tmp_path / "main.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO goods (name, description, format, minimum, price, stored, shop_id) VALUES ('P1','d','txt',1,2,'x',1)")
    cur.execute("INSERT INTO goods (name, description, format, minimum, price, stored, shop_id) VALUES ('P2','d','txt',1,2,'x',2)")
    cur.execute("UPDATE goods SET media_file_id='id1', media_type='photo', media_caption='c1' WHERE name='P1'")
    cur.execute("UPDATE goods SET media_file_id='id2', media_type='photo', media_caption='c2' WHERE name='P2'")
    conn.commit()
    conn.close()

    assert dop.get_product_media('P1', 1) == {'file_id': 'id1', 'type': 'photo', 'caption': 'c1'}
    assert dop.get_product_media('P1', 2) is None

    dop.remove_product_media('P1', 2)
    assert dop.get_product_media('P1', 1) == {'file_id': 'id1', 'type': 'photo', 'caption': 'c1'}

    dop.remove_product_media('P1', 1)
    assert dop.get_product_media('P1', 1) is None


def test_has_and_format_media_respect_shop(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    conn = sqlite3.connect(tmp_path / "main.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO goods (name, description, format, minimum, price, stored, shop_id) VALUES ('P1','d1','txt',1,2,'x',1)"
    )
    cur.execute(
        "INSERT INTO goods (name, description, format, minimum, price, stored, shop_id) VALUES ('P2','d2','txt',1,2,'x',2)"
    )
    cur.execute(
        "UPDATE goods SET media_file_id='id1', media_type='photo', media_caption='c1' WHERE name='P1'"
    )
    cur.execute(
        "UPDATE goods SET media_file_id='id2', media_type='photo', media_caption='c2' WHERE name='P2'"
    )
    conn.commit()
    conn.close()

    assert dop.has_product_media('P1', 1)
    assert not dop.has_product_media('P1', 2)

    assert dop.format_product_with_media('P1', 2) is None
    info = dop.format_product_with_media('P1', 1)
    assert info and 'P1' in info

    dop.remove_product_media('P2', 2)
    assert dop.has_product_media('P1', 1)
