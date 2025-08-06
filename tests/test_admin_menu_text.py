from tests.test_shop_info import setup_main
import types


def test_admin_menu_text_dispatch(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])

    called = {}

    def fake_in_adminka(chat_id, text, username, name):
        called['args'] = (chat_id, text, username, name)

    monkeypatch.setattr(main.adminka, 'in_adminka', fake_in_adminka)

    class Msg:
        def __init__(self, text):
            self.text = text
            self.chat = types.SimpleNamespace(id=1, username='admin')
            self.from_user = types.SimpleNamespace(first_name='Admin')
            self.content_type = 'text'

    main.message_send(Msg('/adm'))
    calls.clear()
    called.clear()

    main.message_send(Msg('📦 Surtido'))

    assert called.get('args') == (1, '📦 Surtido', 'admin', 'Admin')
