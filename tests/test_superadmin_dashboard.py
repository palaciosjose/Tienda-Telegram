import os, sqlite3
import adminka, config
from navigation import nav_system
from tests.test_shop_info import setup_main
import files


def test_superadmin_dashboard_metrics(monkeypatch, tmp_path):
    dop, main, calls, _ = setup_main(monkeypatch, tmp_path)
    config.admin_id = 1
    dop.ensure_database_schema()
    sid1 = dop.create_shop("S1", admin_id=1)
    sid2 = dop.create_shop("S2", admin_id=1)
    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE platform_config (platform TEXT, is_active INTEGER, shop_id INTEGER)")
    cur.execute("INSERT INTO platform_config (platform, is_active, shop_id) VALUES ('telethon',1,?)", (sid1,))
    cur.execute("INSERT INTO platform_config (platform, is_active, shop_id) VALUES ('telethon',0,?)", (sid2,))
    cur.execute("UPDATE shops SET telethon_daemon_status='running' WHERE id=?", (sid1,))
    cur.execute("UPDATE shops SET telethon_daemon_status='stopped' WHERE id=?", (sid2,))
    cur.execute(
        "INSERT INTO purchases (id, username, name_good, amount, price, shop_id) VALUES (1,'u','g',1,50,?)",
        (sid1,),
    )
    cur.execute(
        "INSERT INTO store_topics (store_id, group_id, group_name, topic_id, topic_name) VALUES (?,?,?,?,?)",
        (sid1, '1', 'g', 1, 't1'),
    )
    cur.execute(
        "INSERT INTO campaigns (name, message_text, shop_id) VALUES ('c1','msg',?)",
        (sid1,),
    )
    conn.commit()
    conn.close()
    os.environ['GLOBAL_CAMPAIGN_LIMIT'] = '5'
    os.environ['GLOBAL_TOPIC_LIMIT'] = '10'
    sent = []
    monkeypatch.setattr(adminka, 'send_long_message', lambda b, cid, text, **kw: sent.append(text))
    adminka.show_superadmin_dashboard(5, 1)
    text = "\n".join(sent)
    assert 'Ventas: 1/50' in text
    assert 'Campañas: 1' in text
    assert 'Topics: 1' in text
    assert 'Daemons activos: 1/2' in text
    assert 'Límite campañas/día: 5' in text
    assert 'Topics máximos: 10' in text
    quick = nav_system.get_quick_actions(5, 'superadmin_dashboard')
    callbacks = {c for _, c in quick}
    assert {'admin_list_shops', 'admin_create_shop', 'global_telethon_config', 'admin_bi_report'}.issubset(callbacks)
