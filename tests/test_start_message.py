import types
from tests.test_shop_info import setup_main

def test_client_gets_main_menu(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    dop.set_user_shop(5, sid)

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(dop, "get_sost", lambda cid: False)
    monkeypatch.setattr(dop, "user_loger", lambda chat_id=0: None)

    called = {}

    def fake_send(chat_id, username, name):
        called["args"] = (chat_id, username, name)

    monkeypatch.setattr(main, "send_main_menu", fake_send)

    class Msg:
        def __init__(self):
            self.text = "/start"
            self.chat = types.SimpleNamespace(id=5, username="u")
            self.from_user = types.SimpleNamespace(first_name="N")
            self.content_type = "text"

    main.message_send(Msg())

    assert called.get("args") == (5, "u", "N")


def test_admin_selector_only_on_adm(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    dop.set_user_shop(1, sid)

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(dop, "get_sost", lambda cid: False)
    monkeypatch.setattr(dop, "user_loger", lambda chat_id=0: None)

    sent_menu = {}

    def fake_send(chat_id, username, name):
        sent_menu["args"] = (chat_id, username, name)

    monkeypatch.setattr(main, "send_main_menu", fake_send)

    selector = {}

    def fake_selector(cid, uid):
        selector["args"] = (cid, uid)

    monkeypatch.setattr(main, "show_main_interface", fake_selector)

    class Msg:
        def __init__(self, text):
            self.text = text
            self.chat = types.SimpleNamespace(id=1, username="admin")
            self.from_user = types.SimpleNamespace(first_name="Admin")
            self.content_type = "text"

    main.message_send(Msg("/start"))
    assert sent_menu.get("args") == (1, "admin", "Admin")

    sent_menu.clear()
    main.message_send(Msg("/adm"))
    assert selector.get("args") == (1, 1)
    assert not sent_menu


def test_new_user_start_shows_selector(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    dop.create_shop("S1", admin_id=1)

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(dop, "get_sost", lambda cid: False)
    monkeypatch.setattr(dop, "user_loger", lambda chat_id=0: None)

    called = {}

    def fake_select(chat_id, message=None):
        called["args"] = (chat_id, message)

    monkeypatch.setattr(main, "show_shop_selection", fake_select)

    class Msg:
        def __init__(self):
            self.text = "/start"
            self.chat = types.SimpleNamespace(id=5, username="u")
            self.from_user = types.SimpleNamespace(first_name="N")
            self.content_type = "text"

    main.message_send(Msg())

    assert called.get("args")[0] == 5


def test_interface_superadmin(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    monkeypatch.setattr(main.db, "get_user_role", lambda uid: "superadmin")

    import files, sqlite3
    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE platform_config (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, config_data TEXT, is_active INTEGER, last_updated TEXT, shop_id INTEGER)"
    )
    sid = dop.create_shop("S1", admin_id=1)
    cur.execute(
        "INSERT INTO platform_config (platform, is_active, shop_id) VALUES ('telethon', 0, ?)",
        (sid,),
    )
    conn.commit()
    conn.close()

    calls.clear()
    main.show_main_interface(1, 1)
    # Validate buttons
    markup = calls[-1][2]["reply_markup"]
    texts = [b.text for b in markup.buttons]
    assert "🌟 TIENDA PRINCIPAL - SuperAdmin" in texts
    assert any("S1" in t and "⚪" in t for t in texts)

    # The message body also lists the stores with their indicators
    sent_text = calls[-1][1][1]
    assert "S1" in sent_text and "⚪" in sent_text


def test_interface_regular_user(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    import files, sqlite3
    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE platform_config (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, config_data TEXT, is_active INTEGER, last_updated TEXT, shop_id INTEGER)"
    )
    sid = dop.create_shop("S2", admin_id=2)
    cur.execute(
        "INSERT INTO platform_config (platform, is_active, shop_id) VALUES ('telethon', 1, ?)",
        (sid,),
    )
    conn.commit()
    conn.close()

    calls.clear()
    main.show_main_interface(2, 2)
    # Validate buttons
    markup = calls[-1][2]["reply_markup"]
    texts = [b.text for b in markup.buttons]
    assert "🌟 TIENDA PRINCIPAL - SuperAdmin" not in texts
    assert any("S2" in t and "🤖" in t for t in texts)

    # Ensure the message body reflects the same information
    sent_text = calls[-1][1][1]
    assert "S2" in sent_text and "🤖" in sent_text
