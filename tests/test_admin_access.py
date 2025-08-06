from tests.test_shop_info import setup_main
import types
import os
import config
from navigation import nav_system


def test_adm_command_requires_permissions(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    config.admin_id = 1
    os.environ["TELEGRAM_ADMIN_ID"] = "1"
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

    def fake_show(cid, uid):
        called['args'] = (cid, uid)

    monkeypatch.setattr(main, 'show_main_interface', fake_show)

    class Msg:
        def __init__(self):
            self.text = '/adm'
            self.chat = types.SimpleNamespace(id=1, username='admin')
            self.from_user = types.SimpleNamespace(first_name='Admin')
            self.content_type = 'text'

    main.message_send(Msg())

    assert called.get('args') == (1, 1)


def test_superadmin_dashboard_access(monkeypatch, tmp_path):
    import sys
    sys.modules.pop('adminka', None)
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    config.admin_id = 1
    os.environ["TELEGRAM_ADMIN_ID"] = "1"

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=5)
            self.message_id = 1
            self.content_type = 'text'
            self.from_user = types.SimpleNamespace(first_name='n')

    cb = types.SimpleNamespace(
        data='select_store_main',
        message=Msg(),
        id='1',
        from_user=types.SimpleNamespace(id=1),
    )
    main.inline(cb)
    messages = []
    for c in calls:
        if c[0] == 'send_message':
            if len(c[1]) > 1:
                messages.append(c[1][1])
            else:
                messages.append(c[2].get('text', ''))

    assert any('+----+' in m for m in messages)


def test_superadmin_dashboard_denied(monkeypatch, tmp_path):
    import sys
    sys.modules.pop('adminka', None)
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    config.admin_id = 1
    os.environ["TELEGRAM_ADMIN_ID"] = "1"

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=6)
            self.message_id = 1
            self.content_type = 'text'
            self.from_user = types.SimpleNamespace(first_name='n')

    cb = types.SimpleNamespace(
        data='select_store_main',
        message=Msg(),
        id='1',
        from_user=types.SimpleNamespace(id=2),
    )
    main.inline(cb)
    messages = []
    for c in calls:
        if c[0] == 'send_message':
            if len(c[1]) > 1:
                messages.append(c[1][1])
            else:
                messages.append(c[2].get('text', ''))

    assert any('Acceso restringido' in m for m in messages)


def test_select_store_main_registered(monkeypatch, tmp_path):
    import sys
    sys.modules.pop('adminka', None)
    setup_main(monkeypatch, tmp_path)
    assert 'select_store_main' in nav_system._actions
