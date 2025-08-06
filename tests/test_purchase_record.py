from tests.test_payments import setup_payments


def test_deliver_product_records_purchase(monkeypatch, tmp_path):
    payments, _ = setup_payments(monkeypatch, tmp_path)
    dop = payments.dop
    dop.ensure_database_schema()

    # Registrar un producto para que get_goodformat devuelva algo coherente
    dop.create_product("P", "d", "text", 1, 5, "x", shop_id=1)

    # Stubs para simplificar la entrega del producto
    monkeypatch.setattr(dop, "get_user_shop", lambda cid: 1)
    monkeypatch.setattr(dop, "is_manual_delivery", lambda name: False)
    monkeypatch.setattr(dop, "get_goodformat", lambda name: "text")
    monkeypatch.setattr(dop, "get_tovar", lambda name, shop_id: "data")
    monkeypatch.setattr(dop, "check_message", lambda *a, **k: False)
    monkeypatch.setattr(dop, "get_adminlist", lambda: [])
    monkeypatch.setattr(dop, "new_buyer", lambda *a, **k: None)

    recorded = {}

    def fake_new_buy_improved(*args):
        recorded["args"] = args
        return True

    monkeypatch.setattr(dop, "new_buy_improved", fake_new_buy_improved)

    # Fijar el tiempo para un ID predecible
    monkeypatch.setattr(payments.time, "time", lambda: 12345)

    payments.deliver_product(10, "user", "User", "P", 1, 5, "PayPal")

    assert recorded["args"][0] == 10
    assert recorded["args"][2] == "P"
    assert recorded["args"][4] == 5
    assert recorded["args"][5] == "PayPal"
    assert recorded["args"][6] == "PayPal_10_12345"

