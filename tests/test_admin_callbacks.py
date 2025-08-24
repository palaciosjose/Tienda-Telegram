import types, sys, sqlite3, importlib
from pathlib import Path


class DummyButton:
    def __init__(self, text, callback_data):
        self.text = text
        self.callback_data = callback_data


class DummyMarkup:
    def __init__(self):
        self.keyboard = []

    def add(self, *buttons):
        self.keyboard.append(buttons)


def setup_env(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_ADMIN_ID", "1")
    telebot_stub = types.SimpleNamespace(
        TeleBot=lambda *a, **k: types.SimpleNamespace(),
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=DummyMarkup,
            InlineKeyboardButton=DummyButton,
        ),
    )
    sys.modules["telebot"] = telebot_stub
    sys.modules["bot_instance"] = types.SimpleNamespace(bot=telebot_stub.TeleBot())

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import files
    monkeypatch.setattr(files, "main_db", str(tmp_path / "main.db"))

    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE shops (id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, name TEXT)")
    cur.execute("INSERT INTO shops (id, admin_id, name) VALUES (1,1,'Shop')")
    cur.execute("CREATE TABLE buyers (id INTEGER, username TEXT, payed REAL, shop_id INTEGER)")
    cur.execute("CREATE TABLE purchases (id INTEGER, username TEXT, price REAL, name_good TEXT, shop_id INTEGER)")
    cur.execute("CREATE TABLE categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, shop_id INTEGER)")
    cur.execute("CREATE TABLE discounts (id INTEGER PRIMARY KEY AUTOINCREMENT, percent INTEGER, start_time TEXT, end_time TEXT, category_id INTEGER, shop_id INTEGER)")
    cur.execute("CREATE TABLE shop_users (user_id INTEGER, shop_id INTEGER, is_admin INTEGER)")
    conn.commit(); conn.close()

    sys.modules.pop("db", None)
    sys.modules.pop("dop", None)
    sys.modules.pop("adminka", None)
    importlib.import_module("db")
    importlib.import_module("dop")
    adminka = importlib.import_module("adminka")
    return adminka


import pytest


@pytest.mark.parametrize(
    "callback,page",
    [
        ("ad_resumen", "admin_resumen"),
        ("ad_categorias", "admin_categorias"),
        ("discount_add", "discount_add"),
        ("discount_edit", "discount_edit"),
        ("discount_delete", "discount_delete"),
        ("store_info", "store_info"),
        ("store_admins", "store_admins"),
    ],
)

def test_callbacks_return_interface(monkeypatch, tmp_path, callback, page):
    adminka = setup_env(monkeypatch, tmp_path)
    captured = {}

    def fake_send(bot, chat_id, text, markup=None, **kwargs):
        captured["markup"] = markup

    monkeypatch.setattr(adminka, "send_long_message", fake_send)
    adminka.nav_system.reset(1)
    adminka.nav_system.handle(callback, 1, 1)
    markup = captured.get("markup")
    assert markup is not None
    assert hasattr(markup, "keyboard")
    assert adminka.nav_system.current(1) == page
