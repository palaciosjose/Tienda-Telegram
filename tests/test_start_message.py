import types, os
from tests.test_shop_info import setup_main


def test_start_message_with_media(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    import files
    os.makedirs(tmp_path / "data" / "bd", exist_ok=True)
    monkeypatch.setattr(files, "bot_message_bd", str(tmp_path / "bot.bd"))
    monkeypatch.setattr(files, "sost_bd", str(tmp_path / "sost.bd"))

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(main.adminka.dop, "get_adminlist", lambda: [1])

    keyboard_stub = lambda *a, **k: types.SimpleNamespace(row=lambda *b, **c: None)
    monkeypatch.setattr(main.telebot.types, "ReplyKeyboardMarkup", keyboard_stub, raising=False)
    monkeypatch.setattr(main.adminka.telebot.types, "ReplyKeyboardMarkup", keyboard_stub, raising=False)

    os.makedirs("data/Temp", exist_ok=True)

    saved = {}
    orig_save = dop.save_message

    def fake_save(msg_type, text, file_id=None, media_type=None):
        saved["args"] = (msg_type, text, file_id, media_type)
        return orig_save(msg_type, text, file_id=file_id, media_type=media_type)

    monkeypatch.setattr(dop, "save_message", fake_save)
    monkeypatch.setattr(main.adminka.dop, "save_message", fake_save)

    class Msg:
        def __init__(self, text):
            self.text = text
            self.chat = types.SimpleNamespace(id=1, username="admin")
            self.from_user = types.SimpleNamespace(first_name="Admin")
            self.content_type = "text"

    main.message_send(Msg("/adm"))
    main.message_send(Msg("Cambiar mensaje de inicio (/start)"))
    main.message_send(Msg("Bienvenido username"))

    class Photo:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=1)
            self.photo = [types.SimpleNamespace(file_id="fid")]
            self.video = None
            self.document = None
            self.audio = None
            self.animation = None
            self.caption = None
            self.content_type = "photo"

    main.handle_media_files(Photo())

    assert saved.get("args") == ("start", "Bienvenido username", "fid", "photo")

    calls.clear()
    main.send_main_menu(5, "user", "User")
    photo_calls = [c for c in calls if c[0] == "send_photo"]
    assert photo_calls
    args = photo_calls[-1][1]
    kwargs = photo_calls[-1][2]
    assert args[0] == 5 and args[1] == "fid"
    assert kwargs["caption"] == "Bienvenido user"


def test_interface_superadmin(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

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
