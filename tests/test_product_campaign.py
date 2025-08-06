import types, os, re, shelve
from tests.test_shop_info import setup_main


def slug(name):
    return re.sub(r"[^a-zA-Z0-9]+", "-", name).lower().strip("-")


def test_product_campaign_creates_button(monkeypatch, tmp_path):
    dop, main, calls, bot = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    dop.create_product(
        "Item",
        "d",
        "txt",
        1,
        2,
        "x",
        additional_description="extra",
        media_file_id="fid",
        media_type="photo",
        shop_id=sid,
    )

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(main.adminka.dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(main.adminka.files, "sost_bd", str(tmp_path / "sost.bd"))
    keyboard_stub = lambda *a, **k: types.SimpleNamespace(row=lambda *b, **c: None)
    monkeypatch.setattr(main.adminka.telebot.types, "ReplyKeyboardMarkup", keyboard_stub, raising=False)
    monkeypatch.setattr(main.adminka.advertising, "get_today_stats", lambda: {"sent": 0, "success_rate": 100, "groups": 0})
    created = {}

    def fake_create(data):
        created.update(data)
        return True, "ok"

    monkeypatch.setattr(main.adminka, "create_campaign_from_admin", fake_create)

    main.adminka.finalize_product_campaign(1, sid, "Item")

    assert created["name"] == "Producto Item"
    assert created["message_text"] == "d\nextra"
    assert created["media_file_id"] == "fid"
    assert created["media_type"] == "photo"
    assert created["button1_text"] == "Ver producto"
    assert created["button1_url"].endswith(f"prod_{sid}_" + slug("Item"))


def test_start_param_shows_product(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    dop.create_product("Item2", "d", "txt", 1, 2, "x", shop_id=sid)

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(dop, "get_sost", lambda cid: False)
    monkeypatch.setattr(dop, "user_loger", lambda chat_id=0: None)

    param = f"prod_{sid}_" + slug("Item2")

    class Msg:
        def __init__(self):
            self.text = f"/start {param}"
            self.chat = types.SimpleNamespace(id=5, username="u")
            self.from_user = types.SimpleNamespace(first_name="N")
            self.content_type = "text"

    main.message_send(Msg())

    assert dop.get_user_shop(5) == sid
    texts = []
    for c in calls:
        if c[0] == "send_message":
            texts.append(c[1][1])
        elif c[0] in ("send_photo", "send_video", "send_document", "send_audio", "send_animation"):
            texts.append(c[2].get("caption", ""))
    assert any("Item2" in t for t in texts)


def test_product_selection_triggers_campaign(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    dop.create_product(
        "Prod",
        "desc",
        "txt",
        1,
        2,
        "x",
        additional_description="more",
        media_file_id="mfid",
        media_type="photo",
        shop_id=sid,
    )

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(main.adminka.dop, "get_adminlist", lambda: [1])
    path = str(tmp_path / "sost.bd")
    monkeypatch.setattr(main.adminka.files, "sost_bd", path)
    monkeypatch.setattr(dop.files, "sost_bd", path)
    monkeypatch.setattr(main.adminka.advertising, "get_today_stats", lambda: {"sent": 0, "success_rate": 100, "groups": 0})
    keyboard_stub = lambda *a, **k: types.SimpleNamespace(row=lambda *b, **c: None)
    monkeypatch.setattr(main.adminka.telebot.types, "ReplyKeyboardMarkup", keyboard_stub, raising=False)
    monkeypatch.setattr(main.adminka, "show_marketing_menu", lambda *a, **k: None)

    created = {}

    def fake_create(data):
        created.update(data)
        return True, "ok"

    monkeypatch.setattr(main.adminka, "create_campaign_from_admin", fake_create)

    main.adminka.in_adminka(1, "🛒 Campaña de producto", "admin", "Admin")
    with shelve.open(main.adminka.files.sost_bd) as bd:
        assert bd["1"] == 190

    main.adminka.text_analytics("Prod", 1)

    assert created["message_text"] == "desc\nmore"
    assert created["media_file_id"] == "mfid"
    assert created["media_type"] == "photo"


def test_show_marketing_unified(monkeypatch, tmp_path):
    dop, main, calls, bot = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)

    monkeypatch.setattr(main.adminka, "bot", bot)
    monkeypatch.setattr(main.adminka.advertising, "get_all_campaigns", lambda: [{"id": 1, "status": "active"}])
    monkeypatch.setattr(
        main.adminka,
        "CampaignScheduler",
        lambda *a, **k: types.SimpleNamespace(get_pending_sends=lambda: [1]),
    )
    monkeypatch.setattr(main.adminka.telethon_manager, "get_stats", lambda s: {"active": True})

    main.adminka.show_marketing_unified(5, sid)

    assert calls[-1][0] == "send_message"
    buttons = calls[-1][2]["reply_markup"].buttons
    texts = [b.text for b in buttons]
    assert "➕ Nueva" in texts
    assert "📋 Activas" in texts
    assert "🤖 Telethon" in texts


def test_quick_actions_dispatch(monkeypatch, tmp_path):
    dop, main, calls, bot = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)

    triggered = []

    def qn(chat_id, store_id):
        triggered.append(("new", chat_id, store_id))

    def qt(chat_id, store_id):
        triggered.append(("tele", chat_id, store_id))

    def qs(chat_id, store_id):
        triggered.append(("stats", chat_id, store_id))

    monkeypatch.setattr(main.adminka, "bot", bot)
    monkeypatch.setattr(main.adminka, "quick_new_campaign", qn)
    monkeypatch.setattr(main.adminka, "quick_telethon", qt)
    monkeypatch.setattr(main.adminka, "quick_stats", qs)

    main.adminka.nav_system.register("quick_new_campaign", qn)
    main.adminka.nav_system.register("quick_telethon", qt)
    main.adminka.nav_system.register("quick_stats", qs)

    main.adminka.ad_inline("quick_new_campaign", 1, 0)
    main.adminka.ad_inline("quick_telethon", 1, 0)
    main.adminka.ad_inline("quick_stats", 1, 0)

    assert triggered == [("new", 1, sid), ("tele", 1, sid), ("stats", 1, sid)]

