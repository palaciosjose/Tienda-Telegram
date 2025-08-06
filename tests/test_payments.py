import importlib
import sys
import types
import os
import builtins
from pathlib import Path


def setup_payments(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_ADMIN_ID", "1")

    sys.modules.setdefault(
        "dotenv", types.SimpleNamespace(load_dotenv=lambda *a, **k: None)
    )

    # Provide a minimal Binance SDK stub so payments detects availability
    binance_mod = types.ModuleType("binance")
    client_mod = types.ModuleType("binance.client")
    client_mod.Client = object
    binance_mod.client = client_mod
    sys.modules.setdefault("binance", binance_mod)
    sys.modules.setdefault("binance.client", client_mod)

    telebot_stub = types.SimpleNamespace(
        TeleBot=lambda *a, **k: types.SimpleNamespace(
            send_message=lambda *a, **k: None,
            answer_callback_query=lambda *a, **k: None,
            edit_message_text=lambda *a, **k: None,
            edit_message_caption=lambda *a, **k: None,
            delete_message=lambda *a, **k: None,
        ),
        types=types.SimpleNamespace(
            InlineKeyboardMarkup=lambda *a, **k: types.SimpleNamespace(
                add=lambda *a, **k: None
            ),
            InlineKeyboardButton=lambda *a, **k: None,
        ),
    )
    sys.modules["telebot"] = telebot_stub
    bot_stub = telebot_stub.TeleBot()
    sys.modules["bot_instance"] = types.SimpleNamespace(bot=bot_stub)
    sys.modules.setdefault(
        "requests",
        types.SimpleNamespace(
            post=lambda *a, **k: None,
            get=lambda *a, **k: None,
            __version__="0",
            Session=lambda *a, **k: types.SimpleNamespace(headers={}),
            Response=types.SimpleNamespace,
        ),
    )

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import files

    monkeypatch.setattr(files, "main_db", str(tmp_path / "main.db"))

    sys.modules.pop("payments", None)
    payments = importlib.import_module("payments")

    orig_open = builtins.open

    def fake_open(file, mode="r", encoding=None):
        if isinstance(file, str) and file.startswith("data/Temp/"):
            real = tmp_path / file
            real.parent.mkdir(parents=True, exist_ok=True)
            return orig_open(real, mode, encoding=encoding)
        return orig_open(file, mode, encoding=encoding)

    monkeypatch.setattr(builtins, "open", fake_open)
    return payments, bot_stub


def test_creat_bill_binance_records_payment(tmp_path, monkeypatch):
    payments, _ = setup_payments(monkeypatch, tmp_path)
    monkeypatch.setattr(payments.dop, "get_binancedata", lambda shop_id=1: ("a", "b", "ID"))

    captured = {}

    def dummy_edit(*a, **k):
        captured["text"] = a[2]

    monkeypatch.setattr(payments.dop, "safe_edit_message", dummy_edit)

    payments.creat_bill_binance(5, "cb", 1, 4.5, "Prod", 1)

    assert 5 in payments.pending_payments
    info = payments.pending_payments[5]
    assert info["product"] == "Prod"
    assert info["quantity"] == 1
    assert info["amount"] == 4.5
    assert info["payment_id"].startswith("BIN_5_")
    assert 5 in payments.he_client
    assert captured["text"].startswith("💳")
    assert (tmp_path / "data" / "Temp" / "5.txt").exists()


def test_handle_admin_payment_decision_approves(tmp_path, monkeypatch):
    payments, bot = setup_payments(monkeypatch, tmp_path)

    delivered = {}

    def deliver(*args):
        delivered["args"] = args
        return True

    monkeypatch.setattr(payments, "deliver_product", deliver)
    monkeypatch.setattr(payments.dop, "safe_edit_message", lambda *a, **k: None)

    payments.pending_payments[123] = {
        "payment_id": "PID",
        "amount": 5,
        "product": "Item",
        "quantity": 1,
        "timestamp": 0,
    }
    payments.he_client.append(123)

    with builtins.open("data/Temp/123good_name.txt", "w", encoding="utf-8") as f:
        f.write("Item")

    calls = []
    bot.send_message = lambda *a, **k: calls.append("send")
    bot.answer_callback_query = lambda *a, **k: calls.append("answer")

    payments.handle_admin_payment_decision("APROBAR_PAGO_123", 99, "cid", 1)

    assert delivered["args"][0] == 123
    assert 123 not in payments.pending_payments
    assert 123 not in payments.he_client
    assert "answer" in calls