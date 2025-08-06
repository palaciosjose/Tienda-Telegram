import importlib, sqlite3, sys, types, os
from pathlib import Path


def setup_main(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_ADMIN_ID", "1")
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/bot")
    sys.modules.setdefault(
        "dotenv", types.SimpleNamespace(load_dotenv=lambda *a, **k: None)
    )

    calls = []

    class Bot:
        def message_handler(self, *a, **k):
            def wrapper(f):
                return f
            return wrapper
        def callback_query_handler(self, *a, **k):
            def wrapper(f):
                return f
            return wrapper
        def send_message(self, *a, **k):
            calls.append(("send_message", a, k))
        def send_photo(self, *a, **k):
            calls.append(("send_photo", a, k))
        def send_video(self, *a, **k):
            calls.append(("send_video", a, k))
        def send_document(self, *a, **k):
            calls.append(("send_document", a, k))
        def send_audio(self, *a, **k):
            calls.append(("send_audio", a, k))
        def send_animation(self, *a, **k):
            calls.append(("send_animation", a, k))
        def delete_message(self, *a, **k):
            calls.append(("delete_message", a, k))

    class Markup:
        def __init__(self):
            self.buttons = []
        def add(self, *btns):
            self.buttons.extend(btns)

    class Button:
        def __init__(self, text, callback_data=None, url=None):
            self.text = text
            self.callback_data = callback_data
            self.url = url

    telebot_stub = types.SimpleNamespace(TeleBot=lambda *a, **k: Bot(),
                                         types=types.SimpleNamespace(
                                             InlineKeyboardMarkup=Markup,
                                             InlineKeyboardButton=Button,
                                             Update=types.SimpleNamespace(de_json=lambda d: d)))
    sys.modules["telebot"] = telebot_stub
    bot = telebot_stub.TeleBot()
    sys.modules["bot_instance"] = types.SimpleNamespace(bot=bot)
    sys.modules.setdefault(
        "requests",
        types.SimpleNamespace(
            post=lambda *a, **k: None,
            get=lambda *a, **k: None,
            __version__="0",
            Session=lambda *a, **k: types.SimpleNamespace(headers={}),
            Response=types.SimpleNamespace,
        ),
    )

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import files
    monkeypatch.setattr(files, "main_db", str(tmp_path / "main.db"))

    os.makedirs("data/db", exist_ok=True)
    open("data/db/main_data.db", "w").close()

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
    sys.modules.pop("main", None)
    dop = importlib.import_module("dop")
    main = importlib.import_module("main")

    return dop, main, calls, bot


def test_shop_info_storage(monkeypatch, tmp_path):
    dop, _, _, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    dop.update_shop_info(sid, description="desc", media_file_id="fid", media_type="photo", button1_text="B1", button1_url="u1")
    info = dop.get_shop_info(sid)
    assert info["description"] == "desc"
    assert info["media_file_id"] == "fid"
    assert info["media_type"] == "photo"
    assert info["button1_text"] == "B1"
    assert info["button1_url"] == "u1"


def test_shop_selection_shows_info(monkeypatch, tmp_path):
    dop, main, calls, bot = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    dop.create_product("P", "d", "txt", 1, 2, "x", shop_id=sid)
    dop.update_shop_info(sid, description="desc", media_file_id="fid", media_type="photo", button1_text="B1", button1_url="u1")

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=5)
            self.message_id = 1
            self.content_type = "text"
            self.from_user = types.SimpleNamespace(first_name="a")
    cb = types.SimpleNamespace(data=f"SELECT_SHOP_{sid}", message=Msg(), id="1", from_user=types.SimpleNamespace(username="u"))
    main.inline(cb)
    assert any(c[0] == "send_photo" for c in calls)
    assert any("CATEGORÍA" in c[1][1] for c in calls if c[0] == "send_message")


def test_category_selection_lists_products(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    cid = dop.create_category("Cat", shop_id=sid)
    dop.create_product("P1", "d", "txt", 1, 2, "x", category_id=cid, shop_id=sid)
    dop.create_product("P2", "d", "txt", 1, 2, "x", shop_id=sid)

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=5)
            self.message_id = 1
            self.content_type = "text"
            self.from_user = types.SimpleNamespace(first_name="a")
    msg = Msg()

    cb_shop = types.SimpleNamespace(data=f"SELECT_SHOP_{sid}", message=msg, id="1", from_user=types.SimpleNamespace(username="u"))
    main.inline(cb_shop)
    calls.clear()

    cb_cat = types.SimpleNamespace(data=f"CAT_{cid}", message=msg, id="2", from_user=types.SimpleNamespace(username="u"))
    main.inline(cb_cat)

    messages = [c for c in calls if c[0] == "send_message"]
    msg_texts = []
    for m in messages:
        if len(m[1]) > 1:
            msg_texts.append(m[1][1])
        else:
            msg_texts.append(m[2].get("text", ""))
    assert any("CATÁLOGO" in t for t in msg_texts)
    buttons = messages[-1][2]["reply_markup"].buttons
    btn_texts = [b.text for b in buttons]
    assert any("P1" in t for t in btn_texts)
    assert not any("P2" in t for t in btn_texts)


def test_shop_rating_shown(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    dop.update_shop_info(sid, description="desc")
    dop.submit_shop_rating(sid, 1, 5)
    dop.submit_shop_rating(sid, 2, 4)

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=5)
            self.message_id = 1
            self.content_type = "text"
            self.from_user = types.SimpleNamespace(first_name="a")

    cb = types.SimpleNamespace(data=f"SELECT_SHOP_{sid}", message=Msg(), id="1", from_user=types.SimpleNamespace(username="u"))
    main.inline(cb)

    first = next(c for c in calls if c[0] in ("send_message", "send_photo"))
    if first[0] == "send_photo":
        text = first[2]["caption"]
        buttons = first[2]["reply_markup"].buttons
    else:
        text = first[1][1]
        buttons = first[2]["reply_markup"].buttons

    assert "4.5" in text
    assert any(b.text.startswith("⭐") for b in buttons)


def test_dashboard_has_telethon_button(monkeypatch, tmp_path):
    dop, _, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    import importlib, adminka
    importlib.reload(adminka)
    adminka.show_store_dashboard_unified(5, sid, "S1")
    buttons = calls[-1][2]["reply_markup"].buttons
    texts = [b.text for b in buttons]
    assert any("Telethon" in t for t in texts)
