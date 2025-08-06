import json
import sys
import types
from tests.test_shop_info import setup_main

sys.modules.setdefault(
    "dotenv", types.SimpleNamespace(load_dotenv=lambda *a, **k: None)
)
sys.modules.setdefault(
    "telebot",
    types.SimpleNamespace(
        types=types.SimpleNamespace(Update=types.SimpleNamespace(de_json=lambda d: d)),
        TeleBot=lambda *a, **k: types.SimpleNamespace(),
    ),
)
os = __import__("os")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "x")
os.environ.setdefault("TELEGRAM_ADMIN_ID", "1")
os.environ.setdefault("WEBHOOK_URL", "https://example.com/bot")

try:
    import flask  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal env
    request = types.SimpleNamespace(headers={}, get_json=lambda: None)

    class App:
        def __init__(self, *a, **k):
            self.routes = {}

        def route(self, path, methods=None):
            def decorator(func):
                self.routes[(path, tuple(methods or ["GET"]))] = func
                return func
            return decorator

        def test_client(self):
            app = self

            class Client:
                def post(self, path, json=None, data=None, headers=None):
                    if json is not None:
                        hdrs = {"content-type": "application/json"}
                        if headers:
                            hdrs.update(headers)
                        request.headers = hdrs
                        request.get_json = lambda: json
                    else:
                        request.headers = headers or {}
                        request.get_json = lambda: data
                    resp = app.routes[(path, ("POST",))]()
                    if isinstance(resp, tuple):
                        status = resp[1]
                    else:
                        status = 200
                    return types.SimpleNamespace(status_code=status)

                def get(self, path, headers=None):
                    request.headers = headers or {}
                    resp = app.routes[(path, ("GET",))]()
                    if isinstance(resp, tuple):
                        status = resp[1]
                    else:
                        status = 200
                    return types.SimpleNamespace(status_code=status)

            return Client()

    flask = types.SimpleNamespace(Flask=App, request=request, abort=lambda c: ("", c))
    sys.modules.setdefault("flask", flask)

import webhook_server


def setup_app(monkeypatch, tmp_path):
    dop, main, calls, bot = setup_main(monkeypatch, tmp_path)
    monkeypatch.setattr(main.config, "WEBHOOK_SECRET_TOKEN", "secret", raising=False)
    monkeypatch.setattr(webhook_server.config, "WEBHOOK_SECRET_TOKEN", "secret", raising=False)
    monkeypatch.setattr(webhook_server, "telebot", sys.modules["telebot"], raising=False)
    monkeypatch.setattr(webhook_server, "bot", bot, raising=False)
    # Reset metrics for each test
    monkeypatch.setattr(webhook_server, "metrics", {"requests_total": 0, "updates_total": 0}, raising=False)
    app = webhook_server.create_app()
    return app, webhook_server, calls, bot, main


def test_valid_update(monkeypatch, tmp_path):
    app, server, calls, bot, main = setup_app(monkeypatch, tmp_path)
    monkeypatch.setattr(bot, "process_new_updates", lambda updates: calls.append(("process_new_updates", updates)), raising=False)
    client = app.test_client()
    update = {"update_id": 1}
    before = server.metrics.copy()
    resp = client.post(main.config.WEBHOOK_PATH, json=update, headers={"X-Telegram-Bot-Api-Secret-Token": "secret"})
    assert resp.status_code == 200
    assert any(c[0] == "process_new_updates" for c in calls)
    assert server.metrics["updates_total"] == before["updates_total"] + 1
    assert server.metrics["requests_total"] == before["requests_total"] + 1


def test_invalid_secret(monkeypatch, tmp_path):
    app, server, calls, bot, main = setup_app(monkeypatch, tmp_path)
    monkeypatch.setattr(bot, "process_new_updates", lambda updates: calls.append(("process_new_updates", updates)), raising=False)
    client = app.test_client()
    update = {"update_id": 1}
    before = server.metrics.copy()
    resp = client.post(main.config.WEBHOOK_PATH, json=update, headers={"X-Telegram-Bot-Api-Secret-Token": "bad"})
    assert resp.status_code == 403
    assert not any(c[0] == "process_new_updates" for c in calls)
    assert server.metrics["updates_total"] == before["updates_total"]
    assert server.metrics["requests_total"] == before["requests_total"] + 1


def test_invalid_content_type(monkeypatch, tmp_path):
    app, server, calls, bot, main = setup_app(monkeypatch, tmp_path)
    monkeypatch.setattr(bot, "process_new_updates", lambda updates: calls.append(("process_new_updates", updates)), raising=False)
    client = app.test_client()
    before = server.metrics.copy()
    resp = client.post(main.config.WEBHOOK_PATH, data="notjson", headers={"X-Telegram-Bot-Api-Secret-Token": "secret"})
    assert resp.status_code == 415
    assert not any(c[0] == "process_new_updates" for c in calls)
    assert server.metrics["updates_total"] == before["updates_total"]
    assert server.metrics["requests_total"] == before["requests_total"] + 1
