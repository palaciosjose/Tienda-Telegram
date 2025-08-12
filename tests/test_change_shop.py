import types
from tests.test_shop_info import setup_main


def test_main_menu_has_change_button(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    main.send_main_menu(5, 'u', 'N')
    buttons = calls[-1][2]["reply_markup"].buttons
    assert any('🔄 Cambiar tienda' in b.text for b in buttons)


def test_change_shop_callback_invokes_list(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    captured = {}

    def fake_edit(bot, msg, text, reply_markup=None, parse_mode=None):
        captured['msg'] = msg
        captured['text'] = text
        return True

    monkeypatch.setattr(dop, 'safe_edit_message', fake_edit)
    monkeypatch.setattr(main.bot, 'answer_callback_query', lambda *a, **k: None, raising=False)

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=5)
            self.message_id = 1
            self.content_type = 'text'
            self.from_user = types.SimpleNamespace(first_name='a')

    cb = types.SimpleNamespace(
        data='Cambiar tienda', message=Msg(), id='1', from_user=types.SimpleNamespace(username='u')
    )
    main.inline(cb)

    assert captured.get('msg') is cb.message
    assert captured.get('text') == 'Seleccione una tienda:'


def test_reselect_updates_shop(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    sid1 = dop.create_shop('S1', admin_id=1)
    sid2 = dop.create_shop('S2', admin_id=1)
    dop.set_user_shop(5, sid1)

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=5)
            self.message_id = 1
            self.content_type = 'text'
            self.from_user = types.SimpleNamespace(first_name='a')

    cb = types.SimpleNamespace(data=f'SELECT_SHOP_{sid2}', message=Msg(), id='2', from_user=types.SimpleNamespace(username='u'))
    main.inline(cb)

    assert dop.get_user_shop(5) == sid2
