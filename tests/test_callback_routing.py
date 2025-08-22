import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_superadmin_callback_routing(monkeypatch):
    adminka = importlib.import_module('adminka')
    called = []

    monkeypatch.setattr(adminka, 'admin_list_shops', lambda c, u: called.append('list'))
    monkeypatch.setattr(adminka, 'admin_create_shop', lambda c, u: called.append('create'))
    monkeypatch.setattr(adminka, 'show_bi_report', lambda c, u: called.append('report'))
    monkeypatch.setattr(
        adminka.telethon_config,
        'global_telethon_config',
        lambda data, chat_id, user_id=None: called.append(data),
    )

    for data in [
        'admin_list_shops',
        'admin_create_shop',
        'admin_bi_report',
        'admin_telethon_config',
    ]:
        adminka.route_superadmin_callback(data, 1, 2)

    assert called == ['list', 'create', 'report', 'admin_telethon_config']

    # Remove module so subsequent tests can import a fresh copy with their own
    # bot stubs.
    sys.modules.pop('adminka', None)


def test_product_callback_routing(monkeypatch):
    adminka = importlib.import_module('adminka')
    called = []

    monkeypatch.setattr(
        adminka, 'edit_product', lambda c, s, n: called.append(('edit', n))
    )
    monkeypatch.setattr(
        adminka, 'toggle_product', lambda c, s, n: called.append(('toggle', n))
    )
    monkeypatch.setattr(
        adminka, 'show_product_list', lambda s, c, p=1: called.append(('page', p))
    )

    assert adminka.route_callback('product_edit_X', 1, 2)
    assert adminka.route_callback('product_toggle_Y', 1, 2)
    assert adminka.route_callback('product_page_3', 1, 2)
    assert called == [('edit', 'X'), ('toggle', 'Y'), ('page', 3)]
    assert not adminka.route_callback('unknown', 1, 2)

    sys.modules.pop('adminka', None)
