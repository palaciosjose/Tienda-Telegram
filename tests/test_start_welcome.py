import types
from tests.test_shop_info import setup_main


def test_start_calls_interface_existing_user(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    sid = dop.create_shop("S1", admin_id=1)
    dop.set_user_shop(5, sid)

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(dop, "get_sost", lambda cid: False)
    monkeypatch.setattr(dop, "user_loger", lambda chat_id=0: None)

    called = {}

    def fake_interface(cid, uid):
        called["args"] = (cid, uid)

    monkeypatch.setattr(main, "show_main_interface", fake_interface)

    class Msg:
        def __init__(self):
            self.text = "/start"
            self.chat = types.SimpleNamespace(id=5, username="u")
            self.from_user = types.SimpleNamespace(first_name="N")
            self.content_type = "text"

    main.message_send(Msg())

    assert called.get("args") == (5, 5)


def test_start_calls_interface_new_user(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    dop.create_shop("S1", admin_id=1)

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(dop, "get_sost", lambda cid: False)
    monkeypatch.setattr(dop, "user_loger", lambda chat_id=0: None)

    called = []

    def fake_interface(cid, uid):
        called.append((cid, uid))

    monkeypatch.setattr(main, "show_main_interface", fake_interface)

    class Msg:
        def __init__(self):
            self.text = "/start"
            self.chat = types.SimpleNamespace(id=5, username="u")
            self.from_user = types.SimpleNamespace(first_name="N")
            self.content_type = "text"

    main.message_send(Msg())

    assert called == [(5, 5)]


def test_start_multiple_calls(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    dop.create_shop("S1", admin_id=1)

    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])
    monkeypatch.setattr(dop, "get_sost", lambda cid: False)
    users_file = tmp_path / "users.txt"
    monkeypatch.setattr(dop.files, "users_list", str(users_file))

    called = []

    def fake_interface(cid, uid):
        called.append((cid, uid))

    monkeypatch.setattr(main, "show_main_interface", fake_interface)

    class Msg:
        def __init__(self):
            self.text = "/start"
            self.chat = types.SimpleNamespace(id=5, username="u")
            self.from_user = types.SimpleNamespace(first_name="N")
            self.content_type = "text"

    main.message_send(Msg())
    main.message_send(Msg())

    assert called == [(5, 5), (5, 5)]
    assert not dop.user_has_shop(5)

