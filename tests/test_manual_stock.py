import builtins, importlib, sys, types
from pathlib import Path
from tests.test_payments import setup_payments
import sqlite3
import files


def test_manual_stock_decrements(monkeypatch, tmp_path):
    monkeypatch.setattr(files, "main_db", str(tmp_path / "main.db"))
    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE shops (id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, name TEXT)")
    cur.execute("CREATE TABLE goods (name TEXT, description TEXT, format TEXT, minimum INTEGER, price INTEGER, stored TEXT, shop_id INTEGER DEFAULT 1, PRIMARY KEY (name, shop_id))")
    conn.commit()
    conn.close()

    payments, _ = setup_payments(monkeypatch, tmp_path)
    dop = payments.dop
    dop.ensure_database_schema()
    dop.create_product(
        "M1",
        "desc",
        "manual",
        1,
        2,
        "x",
        manual_delivery=1,
        manual_stock=5,
        shop_id=1,
    )

    monkeypatch.setattr(dop, "get_adminlist", lambda: [])
    monkeypatch.setattr(dop, "check_message", lambda *a, **k: False)
    monkeypatch.setattr(dop, "get_manual_delivery_message", lambda u, n: "msg")

    assert dop.amount_of_goods("M1", 1) == 5
    payments.deliver_product(1, "u", "User", "M1", 2, 4, "PayPal")
    assert dop.amount_of_goods("M1", 1) == 3


def test_manual_stock_modifications(monkeypatch, tmp_path):
    from tests.test_categories import setup_dop

    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    dop.create_product(
        "M2",
        "desc",
        "manual",
        1,
        1,
        "x",
        manual_delivery=1,
        manual_stock=2,
        shop_id=1,
    )

    assert dop.get_manual_stock("M2", 1) == 2
    dop.add_manual_stock("M2", 3, 1)
    assert dop.get_manual_stock("M2", 1) == 5
    dop.set_manual_stock("M2", 10, 1)
    assert dop.get_manual_stock("M2", 1) == 10
