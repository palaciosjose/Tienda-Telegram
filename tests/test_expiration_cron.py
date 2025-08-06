import importlib, sys, sqlite3, types


def test_expiration_cron_uses_env_token(monkeypatch, tmp_path):
    sent = []

    class DummyBot:
        def __init__(self, token):
            self.token = token
        def send_message(self, cid, text):
            sent.append((cid, text))

    monkeypatch.setenv("TELEGRAM_TOKEN", "x")
    sys.modules["telebot"] = types.SimpleNamespace(TeleBot=lambda t: DummyBot(t))
    sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda *a, **k: None))

    import files
    monkeypatch.setattr(files, "main_db", str(tmp_path / "main.db"))

    conn = sqlite3.connect(files.main_db)
    conn.execute(
        "CREATE TABLE purchases (id INTEGER, username TEXT, name_good TEXT, amount INTEGER, price INTEGER, payment_method TEXT, timestamp TEXT, expires_at TEXT, shop_id INTEGER)"
    )
    conn.execute(
        "INSERT INTO purchases VALUES (1, 'u', 'P', 1, 5, 'paypal', 't', '2000-01-01T00:00:00', 1)"
    )
    conn.commit()
    conn.close()

    expiration_cron = importlib.reload(importlib.import_module("expiration_cron"))
    expiration_cron.main()

    assert sent == [(1, 'Tu compra de P ha expirado. Vuelve a comprar si deseas renovarla.')]
