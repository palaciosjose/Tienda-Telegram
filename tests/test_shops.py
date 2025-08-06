import sqlite3, importlib, sys, types
from pathlib import Path

from tests.test_categories import setup_dop


def test_shop_functions(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    # Crear tienda y obtener shop_id
    sid = dop.create_shop("Shop1", admin_id=1)
    assert sid == 1
    assert dop.get_shop_id(1) == sid

    # Crear otra tienda sin admin y luego asignarlo
    sid2 = dop.create_shop("Shop2")
    assert sid2 == 2
    ok = dop.assign_admin_to_shop(sid2, 5)
    assert ok
    assert dop.get_shop_id(5) == sid2

    # Cambiar nombre de la tienda
    renamed = dop.update_shop_name(sid2, "NuevaShop")
    assert renamed
    shops = dop.list_shops()
    assert any(s[0] == sid2 and s[2] == "NuevaShop" for s in shops)
