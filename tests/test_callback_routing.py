import importlib
import sys


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
