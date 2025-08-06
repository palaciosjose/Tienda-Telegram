import importlib, sqlite3, sys, types
from pathlib import Path
import builtins


def setup_dop(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_ADMIN_ID", "1")
    sys.modules.setdefault(
        "dotenv", types.SimpleNamespace(load_dotenv=lambda *a, **k: None)
    )

    telebot_stub = types.SimpleNamespace(
        TeleBot=lambda *a, **k: types.SimpleNamespace(),
        types=types.SimpleNamespace(InlineKeyboardMarkup=lambda *a, **k: None,
                                    InlineKeyboardButton=lambda *a, **k: None),
    )
    sys.modules["telebot"] = telebot_stub
    bot_stub = telebot_stub.TeleBot()
    sys.modules["bot_instance"] = types.SimpleNamespace(bot=bot_stub)

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import files
    monkeypatch.setattr(files, "main_db", str(tmp_path / "main.db"))

    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE shops (id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, name TEXT)")
    cur.execute(
        "CREATE TABLE goods (name TEXT, description TEXT, format TEXT, minimum INTEGER, price INTEGER, stored TEXT, shop_id INTEGER DEFAULT 1, PRIMARY KEY (name, shop_id))"
    )
    conn.commit()
    conn.close()

    sys.modules.pop("db", None)
    sys.modules.pop("dop", None)
    dop = importlib.import_module("dop")
    return dop


def test_category_creation_and_assignment(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    conn = sqlite3.connect(tmp_path / "main.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categories'")
    assert cur.fetchone() is not None

    cur.execute("PRAGMA table_info(categories)")
    cat_cols = [c[1] for c in cur.fetchall()]
    assert "shop_id" in cat_cols

    cur.execute("PRAGMA table_info(goods)")
    cols = [c[1] for c in cur.fetchall()]
    assert "category_id" in cols
    assert "shop_id" in cols

    cat_id = dop.create_category("Test")
    assert cat_id

    cur.execute("INSERT INTO goods (name, description, format, minimum, price, stored, category_id, shop_id) VALUES ('P', 'd', 'text', 1, 2, 'f', ?, 1)", (cat_id,))
    conn.commit()

    cur.execute("SELECT category_id, shop_id FROM goods WHERE name='P'")
    row = cur.fetchone()
    assert row[0] == cat_id
    assert row[1] == 1
    conn.close()


def test_update_category_name(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    cat_id = dop.create_category("Old")
    assert cat_id

    ok = dop.update_category_name(cat_id, "New", 1)
    assert ok
    assert dop.get_category_name(cat_id, 1) == "New"

