import sys
import types
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import telethon_manager
import db
import files
import shelve


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

    progress = []
    summary = telethon_manager.detect_topics(5, progress_callback=progress.append)
    assert "G1 (1): T1 (10)" in summary
    assert "G2 (2): T2 (20)" in summary
    assert any("Procesando" in m for m in progress)
    assert progress[-1] == "Detección finalizada"

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


def test_route_callback_detect_topics(monkeypatch):
    msgs = []
    markups = []

    class DummyBot:
        def send_message(self, chat_id, text, reply_markup=None, **kw):
            msgs.append(text)
            markups.append(reply_markup)

    class Button:
        def __init__(self, text, callback_data=None):
            self.text = text
            self.callback_data = callback_data

    class Markup:
        def __init__(self):
            self.keyboard = []

        def add(self, *buttons):
            self.keyboard.append(list(buttons))

    telebot_stub = types.SimpleNamespace(
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=Markup,
            InlineKeyboardButton=Button,
        )
    )
    monkeypatch.setitem(sys.modules, "telebot", telebot_stub)
    monkeypatch.setitem(sys.modules, "bot_instance", types.SimpleNamespace(bot=None))
    import importlib
    sys.modules.pop("streaming_manager_bot", None)
    streaming_module = importlib.import_module("streaming_manager_bot")

    def fake_send(bot, chat_id, text, markup=None, parse_mode=None):
        msgs.append(text)
        markups.append(markup)

    monkeypatch.setattr(streaming_module, "send_long_message", fake_send)
    monkeypatch.setattr(telethon_manager, "detect_topics", lambda s: "resumen")

    smb = streaming_module.StreamingManagerBot(DummyBot())
    smb.route_callback("telethon_detect_5", 99)

    assert msgs == ["resumen"]
    buttons = [b.text for row in markups[0].keyboard for b in row]
    assert "Seleccionar todos" in buttons
    assert "Personalizar" in buttons


def test_wizard_progress_and_auto_selection(monkeypatch, tmp_path):
    """The telethon wizard should save progress and show progress bars."""

    _setup_tmp_db(tmp_path, monkeypatch)

    msgs = []
    actions = []

    class Bot:
        def send_message(self, chat_id, text, **kw):
            msgs.append(text)

    class Markup:
        pass

    telebot_stub = types.SimpleNamespace(
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=lambda: Markup(),
            InlineKeyboardButton=lambda *a, **k: None,
        )
    )

    monkeypatch.setitem(sys.modules, "telebot", telebot_stub)
    monkeypatch.setitem(sys.modules, "bot_instance", types.SimpleNamespace(bot=Bot()))

    import importlib, telethon_config
    importlib.reload(telethon_config)

    monkeypatch.setattr(telethon_config.files, "sost_bd", str(tmp_path / "sost.bd"))
    monkeypatch.setattr(
        telethon_config.db,
        "get_global_telethon_status",
        lambda: {"api_id": "1", "api_hash": "2"},
    )

    def fake_detect(store_id, progress_callback=lambda m: None):
        progress_callback("[##------] 20%")
        return "resumen"

    def fake_auto(store_id, progress_callback=lambda m: None):
        progress_callback("[######--] 60%")
        return True

    monkeypatch.setattr(telethon_config.telethon_manager, "detect_topics", fake_detect)
    monkeypatch.setattr(telethon_config.telethon_manager, "start_auto_detection", fake_auto)
    monkeypatch.setattr(
        telethon_config.telethon_manager, "test_send", lambda s: actions.append("test")
    )
    monkeypatch.setattr(
        telethon_config.telethon_manager,
        "restart_daemon",
        lambda s: actions.append("activate"),
    )

    telethon_config.start_telethon_wizard(1, 5)
    with shelve.open(telethon_config.files.sost_bd) as bd:
        assert bd["1_telethon_step"] == 1
    telethon_config.start_telethon_wizard(1, 5)
    with shelve.open(telethon_config.files.sost_bd) as bd:
        assert bd["1_telethon_step"] == 2
    telethon_config.start_telethon_wizard(1, 5)
    with shelve.open(telethon_config.files.sost_bd) as bd:
        assert "1_telethon_step" not in bd

    assert "resumen" in msgs
    assert any(m.startswith("[") for m in msgs)
    assert actions == ["test", "activate"]

