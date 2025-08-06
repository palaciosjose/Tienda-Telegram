import sys
import types
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import telethon_manager
import db
import files


def _setup_tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "main.db"
    monkeypatch.setattr(files, "main_db", str(db_path))
    db.close_connection()
    con = db.get_db_connection()
    con.commit()


def test_detect_topics_saves_and_returns_summary(tmp_path, monkeypatch):
    _setup_tmp_db(tmp_path, monkeypatch)

    class DummyTopic:
        def __init__(self, id, title):
            self.id = id
            self.title = title

    class DummyDialog:
        def __init__(self, id, name):
            self.name = name
            self.entity = types.SimpleNamespace(id=id)

    class DummyClient:
        def __init__(self, *a, **k):
            pass

        def connect(self):
            pass

        def disconnect(self):
            pass

        def iter_dialogs(self):
            return [DummyDialog(1, "G1"), DummyDialog(2, "G2")]

        def __call__(self, req):
            if req.channel.id == 1:
                return types.SimpleNamespace(topics=[DummyTopic(10, "T1")])
            return types.SimpleNamespace(topics=[DummyTopic(20, "T2")])

    class DummyRequest:
        def __init__(self, channel, **kw):
            self.channel = channel

    monkeypatch.setattr(telethon_manager, "TelegramClient", DummyClient)
    monkeypatch.setattr(telethon_manager, "GetForumTopicsRequest", DummyRequest)

    summary = telethon_manager.detect_topics(5)
    assert "G1 (1): T1 (10)" in summary
    assert "G2 (2): T2 (20)" in summary

    con = db.get_db_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT store_id, group_id, topic_id FROM store_topics ORDER BY group_id"
    )
    rows = cur.fetchall()
    assert rows == [(5, "1", 10), (5, "2", 20)]


def test_start_auto_detection_progress():
    msgs = []
    telethon_manager.start_auto_detection(
        1, progress_callback=lambda m: msgs.append(m)
    )
    assert msgs[0].startswith("[")
    assert msgs[-1].endswith("100%")


def test_route_callback_start_auto_detection(monkeypatch):
    msgs = []

    class DummyBot:
        def send_message(self, chat_id, text, **kw):
            msgs.append(text)
    monkeypatch.setitem(sys.modules, "bot_instance", types.SimpleNamespace(bot=None))
    import importlib
    streaming_module = importlib.import_module("streaming_manager_bot")
    smb = streaming_module.StreamingManagerBot(DummyBot())

    def fake_start(store_id, mode, progress):
        progress("[#####-----] 50%")

    monkeypatch.setattr(telethon_manager, "start_auto_detection", fake_start)
    smb.route_callback("start_auto_detection_7_all", 99)

    assert msgs == ["[#####-----] 50%", "Configuración confirmada"]

