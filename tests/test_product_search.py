import types
import os
import shelve
from tests.test_shop_info import setup_main


def test_menu_has_search_button(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    main.send_main_menu(5, 'user', 'Name')
    buttons = calls[-1][2]['reply_markup'].buttons
    assert any('🔍 Buscar' in b.text for b in buttons)


def test_search_flow_returns_results(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    sid1 = dop.create_shop('Shop1', admin_id=1)
    sid2 = dop.create_shop('Shop2', admin_id=1)
    dop.create_product('Widget1', 'd1', 'txt', 1, 10, 'x', shop_id=sid1)
    dop.create_product('Widget2', 'd2', 'txt', 1, 20, 'x', shop_id=sid2)

    monkeypatch.setattr(main.files, 'sost_bd', str(tmp_path / 'sost.bd'))
    monkeypatch.setattr(main.bot, 'answer_callback_query', lambda *a, **k: None, raising=False)

    def fake_edit(bot, msg, text, reply_markup=None, parse_mode=None):
        return True

    monkeypatch.setattr(dop, 'safe_edit_message', fake_edit)

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=5, username='u')
            self.message_id = 1
            self.content_type = 'text'
            self.from_user = types.SimpleNamespace(first_name='N')

    cb = types.SimpleNamespace(data='Buscar productos', message=Msg(), id='1', from_user=types.SimpleNamespace(username='u'))
    main.inline(cb)

    with shelve.open(main.files.sost_bd) as bd:
        assert bd[str(cb.message.chat.id)] == 24

    query_msg = types.SimpleNamespace(text='Widget', chat=types.SimpleNamespace(id=5, username='u'), from_user=types.SimpleNamespace(first_name='N'), content_type='text')
    main.message_send(query_msg)

    with shelve.open(main.files.sost_bd) as bd:
        assert str(cb.message.chat.id) not in bd

    assert calls[-1][0] == 'send_message'
    sent_text = calls[-1][1][1]
    assert 'Widget1' in sent_text and 'Widget2' in sent_text


def test_search_results_selectable(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    dop.ensure_database_schema()

    sid = dop.create_shop('Shop', admin_id=1)
    dop.create_product('Item', 'd', 'txt', 1, 5, 'x', shop_id=sid)

    monkeypatch.setattr(main.files, 'sost_bd', str(tmp_path / 'sost.bd'))
    monkeypatch.setattr(main.bot, 'answer_callback_query', lambda *a, **k: None, raising=False)
    monkeypatch.setattr(dop, 'safe_edit_message', lambda *a, **k: True)

    os.makedirs('data/Temp', exist_ok=True)

    class Msg:
        def __init__(self):
            self.chat = types.SimpleNamespace(id=5, username='u')
            self.message_id = 1
            self.content_type = 'text'
            self.from_user = types.SimpleNamespace(first_name='N')

    cb = types.SimpleNamespace(data='Buscar productos', message=Msg(), id='1', from_user=types.SimpleNamespace(username='u'))
    main.inline(cb)

    query_msg = types.SimpleNamespace(text='Item', chat=types.SimpleNamespace(id=5, username='u'), from_user=types.SimpleNamespace(first_name='N'), content_type='text')
    main.message_send(query_msg)

    buttons = [b for b in calls[-1][2]['reply_markup'].buttons if b.text != '🏠 Inicio']
    assert buttons
    cb_select = types.SimpleNamespace(data=buttons[0].callback_data, message=Msg(), id='2', from_user=types.SimpleNamespace(username='u'))
    main.inline(cb_select)

    with open('data/Temp/5good_name.txt', encoding='utf-8') as f:
        assert f.read() == 'Item'
    assert dop.get_user_shop(5) == sid
