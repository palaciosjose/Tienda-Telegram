import importlib
import sys
import os

sys.path.append(os.getcwd())

from tests.test_categories import setup_dop


def setup_admin(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    sys.modules.pop("advertising_system.admin_integration", None)
    admin_int = importlib.import_module("advertising_system.admin_integration")
    admin_int.set_shop_id(1)
    return dop, admin_int


def test_campaign_limit_enforced(monkeypatch, tmp_path):
    dop, admin_int = setup_admin(monkeypatch, tmp_path)
    shop_id = dop.create_shop("Shop1", admin_id=2)
    dop.set_campaign_limit(shop_id, 1)

    ok, msg = admin_int.create_campaign_from_admin(
        {"name": "A", "message_text": "x", "created_by": 2, "shop_id": shop_id}
    )
    assert ok

    ok2, msg2 = admin_int.create_campaign_from_admin(
        {"name": "B", "message_text": "y", "created_by": 2, "shop_id": shop_id}
    )
    assert not ok2
    assert "Límite" in msg2
    ok3, _ = admin_int.create_campaign_from_admin(
        {"name": "C", "message_text": "z", "created_by": 1, "shop_id": shop_id}
    )
    assert ok3


def test_daily_campaign_limit(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    shop_id = dop.create_shop("Shop1", admin_id=2)

    import db

    db.set_daily_campaign_limit(shop_id, 2)
    assert db.register_campaign_send(shop_id)
    assert db.register_campaign_send(shop_id)
    assert not db.register_campaign_send(shop_id)
    db.reset_daily_campaigns(shop_id)
    assert db.register_campaign_send(shop_id)

