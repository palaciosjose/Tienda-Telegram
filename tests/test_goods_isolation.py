import sqlite3
from tests.test_categories import setup_dop


def test_same_product_name_different_shops(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    assert dop.create_shop("S1", admin_id=1) == 1
    assert dop.create_shop("S2", admin_id=2) == 2

    ok1 = dop.create_product("Prod", "d1", "txt", 1, 5, "f1", shop_id=1)
    ok2 = dop.create_product("Prod", "d2", "txt", 1, 10, "f2", shop_id=2)
    assert ok1 and ok2

    desc1 = dop.get_description("Prod", 1)
    desc2 = dop.get_description("Prod", 2)
    assert "d1" in desc1
    assert "d2" in desc2
