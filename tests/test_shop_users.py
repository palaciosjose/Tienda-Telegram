import sqlite3
from tests.test_categories import setup_dop


class DummyBot:
    def __init__(self):
        self.sent = []

    def send_message(self, cid, text):
        self.sent.append((cid, text))


def test_shop_user_registration_and_broadcast(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    # Reemplazar bot por stub
    bot = DummyBot()
    monkeypatch.setattr(dop, "bot", bot)

    dop.set_user_shop(1, 1)
    dop.set_user_shop(2, 2)

    res = dop.broadcast_message("all", 10, "hi", shop_id=1)
    assert "usuarios" in res
    assert bot.sent == [(1, "hi")]
    bot.sent.clear()

    res = dop.broadcast_message("all", 10, "hello", shop_id=2)
    assert bot.sent == [(2, "hello")]

    conn = sqlite3.connect(tmp_path / "main.db")
    cur = conn.cursor()
    cur.execute("SELECT shop_id FROM shop_users WHERE user_id=1")
    row = cur.fetchone()
    assert row and row[0] == 1
    conn.close()
