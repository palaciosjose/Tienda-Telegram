import sqlite3
from tests.test_categories import setup_dop


def test_discount_config_table_created(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    dop.get_discount_config()

    conn = sqlite3.connect(tmp_path / "main.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='discount_config'")
    assert cur.fetchone() is not None

    cur.execute("PRAGMA table_info(discount_config)")
    cols = [c[1] for c in cur.fetchall()]
    expected = {"discount_enabled", "discount_text", "discount_multiplier", "show_fake_price", "shop_id"}
    assert expected.issubset(set(cols))
    conn.close()
