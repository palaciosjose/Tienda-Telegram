import importlib, sqlite3, sys, types
from pathlib import Path


def setup_admin_int(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_ADMIN_ID", "1")
    sys.modules.setdefault(
        "dotenv", types.SimpleNamespace(load_dotenv=lambda *a, **k: None)
    )

    class Bot:
        def __init__(self):
            self.status_map = {}

        def get_chat_member(self, gid, uid):
            status = self.status_map.get(str(gid), "member")
            return types.SimpleNamespace(status=status)

    telebot_stub = types.SimpleNamespace(
        TeleBot=lambda *a, **k: Bot(),
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=lambda *a, **k: None,
            InlineKeyboardButton=lambda *a, **k: None,
        ),
    )
    sys.modules["telebot"] = telebot_stub
    bot = telebot_stub.TeleBot()
    sys.modules["bot_instance"] = types.SimpleNamespace(bot=bot)

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import files
    monkeypatch.setattr(files, "main_db", str(tmp_path / "main.db"))

    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE bot_groups (group_id TEXT PRIMARY KEY, group_name TEXT, added_date TEXT)"
    )
    conn.commit()
    conn.close()

    sys.modules.pop("db", None)
    sys.modules.pop("advertising_system.admin_integration", None)
    admin_int = importlib.import_module("advertising_system.admin_integration")
    return admin_int, bot


def test_add_and_remove_group(monkeypatch, tmp_path):
    admin_int, _ = setup_admin_int(monkeypatch, tmp_path)
    assert admin_int.add_bot_group("123", "Test")
    conn = sqlite3.connect(tmp_path / "main.db")
    cur = conn.cursor()
    cur.execute("SELECT group_name FROM bot_groups WHERE group_id='123'")
    assert cur.fetchone()[0] == "Test"
    assert admin_int.remove_bot_group("123")
    cur.execute("SELECT 1 FROM bot_groups WHERE group_id='123'")
    assert cur.fetchone() is None
    conn.close()


def test_get_admin_groups_filters(monkeypatch, tmp_path):
    admin_int, bot = setup_admin_int(monkeypatch, tmp_path)
    admin_int.add_bot_group("111", "A")
    admin_int.add_bot_group("222", "B")
    bot.status_map["111"] = "administrator"
    bot.status_map["222"] = "left"
    groups = admin_int.get_admin_telegram_groups(bot, 1)
    assert groups == [{"id": "111", "title": "A"}]

