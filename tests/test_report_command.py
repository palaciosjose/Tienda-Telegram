from tests.test_shop_info import setup_main
import shelve, types, os


def test_report_command_sets_state(monkeypatch, tmp_path):
    dop, main, calls, bot = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    os.makedirs('data/bd', exist_ok=True)
    monkeypatch.setattr(main.files, 'sost_bd', str(tmp_path / 'sost.bd'))
    monkeypatch.setattr(main.bot, 'get_me', lambda: types.SimpleNamespace(username='mybot'), raising=False)
    main.bot_username = main.bot.get_me().username.lower()

    class Msg:
        def __init__(self, text):
            self.text = text
            self.chat = types.SimpleNamespace(id=5, username='u')
            self.from_user = types.SimpleNamespace(first_name='N')
    msg = Msg('/report@mybot')
    main.message_send(msg)
    with shelve.open(main.files.sost_bd) as bd:
        assert bd[str(msg.chat.id)] == 23
    assert any(c[0] == 'send_message' for c in calls)


def test_whitespace_message_ignored(monkeypatch, tmp_path):
    dop, main, calls, bot = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    class Msg:
        def __init__(self, text):
            self.text = text
            self.chat = types.SimpleNamespace(id=5, username='u')
            self.from_user = types.SimpleNamespace(first_name='N')

    msg = Msg('   ')
    main.message_send(msg)

    assert not any('Por favor escribe tu reporte' in c[1][1] for c in calls if c[0] == 'send_message')


def test_report_text_forwarded(monkeypatch, tmp_path):
    dop, main, calls, bot = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()
    os.makedirs('data/bd', exist_ok=True)
    monkeypatch.setattr(main.files, 'sost_bd', str(tmp_path / 'sost.bd'))

    with shelve.open(main.files.sost_bd) as bd:
        bd['5'] = 23

    monkeypatch.setattr(main.config, 'admin_id', 99)

    menu_called = {}

    def fake_menu(chat_id, username, name):
        menu_called['args'] = (chat_id, username, name)

    monkeypatch.setattr(main, 'send_main_menu', fake_menu)

    class Msg:
        def __init__(self, text):
            self.text = text
            self.chat = types.SimpleNamespace(id=5, username='u')
            self.from_user = types.SimpleNamespace(first_name='N')

    msg = Msg('algo malo')
    main.message_send(msg)

    with shelve.open(main.files.sost_bd) as bd:
        assert str(msg.chat.id) not in bd

    assert any(c[0] == 'send_message' and c[1][0] == 99 for c in calls)
    assert menu_called.get('args') == (5, 'u', 'N')
