import types
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from test_shop_info import setup_main


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


def test_admin_start_shows_interface(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    dop.set_user_shop(1, sid)

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(dop, "get_sost", lambda cid: False)
    monkeypatch.setattr(dop, "user_loger", lambda chat_id=0: None)

    called = {}

    def fake_interface(chat_id, user_id):
        called["args"] = (chat_id, user_id)

    monkeypatch.setattr(main, "show_main_interface", fake_interface)

    class Msg:
        def __init__(self):
            self.text = "/start"
            self.chat = types.SimpleNamespace(id=1, username="admin")
            self.from_user = types.SimpleNamespace(first_name="Admin")
            self.content_type = "text"

    main.message_send(Msg())
    assert called.get("args") == (1, 1)


def test_shop_callback_loads_dashboard(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    import sys
    sys.modules.pop('adminka', None)
    import adminka
    main.adminka = adminka
    import config, os
    config.admin_id = 999
    os.environ["TELEGRAM_ADMIN_ID"] = "999"
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    import sqlite3, files
    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE platform_config (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, config_data TEXT, is_active INTEGER, last_updated TEXT, shop_id INTEGER)"
    )
    cur.execute(
        "INSERT INTO platform_config (platform, is_active, shop_id) VALUES ('telethon', 0, ?)",
        (sid,),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])

    called = {}

    def fake_dash(cid, sid_arg, name):
        called["args"] = (cid, sid_arg, name)

    monkeypatch.setattr(adminka, "show_store_dashboard_unified", fake_dash)

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=1)
            self.message_id = 1
            self.content_type = "text"
            self.from_user = types.SimpleNamespace(first_name="n")

    cb = types.SimpleNamespace(
        data=f"SHOP_{sid}",
        message=Msg(),
        id="1",
        from_user=types.SimpleNamespace(id=1),
    )
    main.inline(cb)

    assert called.get("args") == (1, sid, "S1")


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
    markup = calls[-1][2]["reply_markup"]
    texts = [b.text for b in markup.buttons]
    assert "🌟 TIENDA PRINCIPAL - SuperAdmin" in texts
    assert any("S1" in t and "⚪" in t for t in texts)

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
    markup = calls[-1][2]["reply_markup"]
    texts = [b.text for b in markup.buttons]
    assert "🌟 TIENDA PRINCIPAL - SuperAdmin" not in texts
    assert any("S2" in t and "🤖" in t for t in texts)

    sent_text = calls[-1][1][1]
    assert "S2" in sent_text and "🤖" in sent_text


def test_interface_pagination(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    import files, sqlite3
    sids = [dop.create_shop(f"S{i}", admin_id=1) for i in range(500)]
    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE platform_config (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, config_data TEXT, is_active INTEGER, last_updated TEXT, shop_id INTEGER)"
    )
    cur.executemany(
        "INSERT INTO platform_config (platform, is_active, shop_id) VALUES ('telethon', 0, ?)",
        [(sid,) for sid in sids],
    )
    conn.commit()
    conn.close()

    calls.clear()
    main.show_main_interface(1, 1)
    send_calls = [c for c in calls if c[0] == "send_message"]
    assert len(send_calls) > 1
    assert send_calls[0][1][1].startswith("1/")
    assert send_calls[1][1][1].startswith("2/")
    assert send_calls[0][2].get("reply_markup") is not None
    assert send_calls[1][2].get("reply_markup") is None

