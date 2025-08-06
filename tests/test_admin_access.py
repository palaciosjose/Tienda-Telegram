from tests.test_shop_info import setup_main
import types


def test_adm_command_requires_permissions(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])

    class Msg:
        def __init__(self):
            self.text = '/adm'
            self.chat = types.SimpleNamespace(id=5, username='user')
            self.from_user = types.SimpleNamespace(first_name='User')
            self.content_type = 'text'

    main.message_send(Msg())

    assert any('No tienes permisos' in c[1][1] for c in calls if c[0] == 'send_message')


def test_adm_command_allows_admin(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])

    called = {}

    def fake_in_adminka(chat_id, text, username, name):
        called['args'] = (chat_id, text, username, name)

    monkeypatch.setattr(main.adminka, 'in_adminka', fake_in_adminka)

    class Msg:
        def __init__(self):
            self.text = '/adm'
            self.chat = types.SimpleNamespace(id=1, username='admin')
            self.from_user = types.SimpleNamespace(first_name='Admin')
            self.content_type = 'text'

    main.message_send(Msg())

    assert called.get('args') == (1, '/adm', 'admin', 'Admin')


def test_admin_panel_button_dispatch(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])

    called = {}

    def fake_in_adminka(chat_id, text, username, name):
        called['args'] = (chat_id, text, username, name)

    monkeypatch.setattr(main.adminka, 'in_adminka', fake_in_adminka)
    monkeypatch.setattr(dop, 'get_sost', lambda chat_id: False)
    main.in_admin.append(1)

    class Msg:
        def __init__(self):
            self.text = '⚙️ Configuración'
            self.chat = types.SimpleNamespace(id=1, username='admin')
            self.from_user = types.SimpleNamespace(first_name='Admin')
            self.content_type = 'text'

    main.message_send(Msg())

    assert called.get('args') == (1, '⚙️ Configuración', 'admin', 'Admin')
