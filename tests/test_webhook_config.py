import importlib
import sys
import types
import pytest


def test_import_requires_webhook_url(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_ADMIN_ID", "1")
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    sys.modules.setdefault(
        "dotenv", types.SimpleNamespace(load_dotenv=lambda *a, **k: None)
    )
    sys.modules.pop("config", None)
    with pytest.raises(RuntimeError):
        importlib.import_module("config")
