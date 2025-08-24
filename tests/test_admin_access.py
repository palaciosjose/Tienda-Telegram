from tests.test_shop_info import setup_main
import types
import os
import config
from navigation import nav_system


def test_adm_command_requires_permissions(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    import sqlite3, files
    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE platform_config (platform TEXT, is_active INTEGER, shop_id INTEGER)")
    cur.execute("INSERT INTO platform_config (platform, is_active, shop_id) VALUES ('telethon', 0, ?)", (sid,))
    conn.commit()
    conn.close()
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
    cur.execute("CREATE TABLE platform_config (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, config_data TEXT, is_active INTEGER, last_updated TEXT, shop_id INTEGER)")
    cur.execute("INSERT INTO platform_config (platform, is_active, shop_id) VALUES ('telethon', 0, ?)", (sid,))
    conn.commit()
    conn.close()
    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])

    called = {}

    def fake_dash(cid, sid_arg, name):
        called['args'] = (cid, sid_arg, name)

    monkeypatch.setattr(adminka, 'show_store_dashboard_unified', fake_dash)

    class Msg:
        def __init__(self):
            self.text = '/adm'
            self.chat = types.SimpleNamespace(id=1, username='admin')
            self.from_user = types.SimpleNamespace(first_name='Admin')
            self.content_type = 'text'

    main.message_send(Msg())

    assert called.get('args') == (1, sid, 'S1')


def test_adm_command_superadmin_dashboard(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    import sqlite3, files
    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE platform_config (platform TEXT, is_active INTEGER, shop_id INTEGER)")
    cur.execute("INSERT INTO platform_config (platform, is_active, shop_id) VALUES ('telethon', 0, ?)", (sid,))
    conn.commit()
    conn.close()
    config.admin_id = 1
    os.environ["TELEGRAM_ADMIN_ID"] = "1"
    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])

    called = {}

    def fake_interface(cid, uid):
        called['args'] = (cid, uid)

    monkeypatch.setattr(main, 'show_main_interface', fake_interface)

    class Msg:
        def __init__(self):
            self.text = '/adm'
            self.chat = types.SimpleNamespace(id=1, username='admin')
            self.from_user = types.SimpleNamespace(first_name='Admin')
            self.content_type = 'text'

    main.message_send(Msg())

    assert called.get('args') == (1, 1)


def test_adm_command_superadmin_role(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    import config, os
    config.admin_id = 42
    os.environ["TELEGRAM_ADMIN_ID"] = "42"
    monkeypatch.setattr(dop, "get_adminlist", lambda: [])
    monkeypatch.setattr(main.db, "get_user_role", lambda uid: "superadmin")

    called = {}

    def fake_interface(cid, uid):
        called['args'] = (cid, uid)

    monkeypatch.setattr(main, 'show_main_interface', fake_interface)

    class Msg:
        def __init__(self):
            self.text = '/adm'
            self.chat = types.SimpleNamespace(id=42, username='owner')
            self.from_user = types.SimpleNamespace(first_name='Owner')
            self.content_type = 'text'

    main.message_send(Msg())

    assert called.get('args') == (42, 42)


def test_shop_callback_opens_dashboard(monkeypatch, tmp_path):
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
    cur.execute("CREATE TABLE platform_config (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, config_data TEXT, is_active INTEGER, last_updated TEXT, shop_id INTEGER)")
    cur.execute("INSERT INTO platform_config (platform, is_active, shop_id) VALUES ('telethon', 0, ?)", (sid,))
    conn.commit()
    conn.close()
    monkeypatch.setattr(dop, "get_adminlist", lambda: [1])

    called = {}

    def fake_dash(cid, sid_arg, name):
        called['args'] = (cid, sid_arg, name)

    monkeypatch.setattr(adminka, 'show_store_dashboard_unified', fake_dash)

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=1)
            self.message_id = 1
            self.content_type = 'text'
            self.from_user = types.SimpleNamespace(first_name='n')

    cb = types.SimpleNamespace(
        data=f'SHOP_{sid}',
        message=Msg(),
        id='1',
        from_user=types.SimpleNamespace(id=1),
    )
    main.inline(cb)

    assert called.get('args') == (1, sid, 'S1')


def test_superadmin_dashboard_access(monkeypatch, tmp_path):
    import sys
    sys.modules.pop('adminka', None)
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    sid = dop.create_shop("S1", admin_id=1)
    import sqlite3, files
    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE platform_config (platform TEXT, is_active INTEGER, shop_id INTEGER)")
    cur.execute("INSERT INTO platform_config (platform, is_active, shop_id) VALUES ('telethon', 0, ?)", (sid,))
    conn.commit()
    conn.close()
    config.admin_id = 1
    os.environ["TELEGRAM_ADMIN_ID"] = "1"

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=5)
            self.message_id = 1
            self.content_type = 'text'
            self.from_user = types.SimpleNamespace(first_name='n')

    called = {'dash': 0}
    import adminka as adm
    original = adm.show_superadmin_dashboard

    sent_texts = []

    def fake_send(bot, cid, text, **kw):
        sent_texts.append(text)

    monkeypatch.setattr(adm, 'send_long_message', fake_send)

    def wrapper(cid, uid):
        called['dash'] += 1
        return original(cid, uid)

    monkeypatch.setattr(adm, 'show_superadmin_dashboard', wrapper)

    cb = types.SimpleNamespace(
        data='select_store_main',
        message=Msg(),
        id='1',
        from_user=types.SimpleNamespace(id=1),
    )
    main.inline(cb)
    assert any('Topics' in m and 'Campañas' in m and 'Daemon' in m for m in sent_texts)
    assert nav_system.current(5) == 'superadmin_dashboard'
    quick = nav_system.get_quick_actions(5, 'superadmin_dashboard')
    texts = {t for t, _ in quick}
    assert {'🏪 Tiendas', '➕ Crear Tienda', '📊 BI Reporte', '🤖 Telethon Global'}.issubset(texts)

    cb = types.SimpleNamespace(
        data='GLOBAL_REFRESH',
        message=Msg(),
        id='2',
        from_user=types.SimpleNamespace(id=1),
    )
    main.inline(cb)
    assert called['dash'] == 2

    monkeypatch.setattr(dop, 'list_shops', lambda: [])
    cb = types.SimpleNamespace(
        data='admin_list_shops',
        message=Msg(),
        id='3',
        from_user=types.SimpleNamespace(id=1),
    )
    main.inline(cb)

    cb = types.SimpleNamespace(
        data='GLOBAL_BACK',
        message=Msg(),
        id='4',
        from_user=types.SimpleNamespace(id=1),
    )
    main.inline(cb)
    assert called['dash'] == 3


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
    assert 'superadmin_dashboard' in nav_system._actions
