from flask import Flask, request, abort
import telebot
import config
from bot_instance import bot

# Simple in-memory metrics
metrics = {
    "requests_total": 0,
    "updates_total": 0,
}


def create_app():
    app = Flask(__name__)
    secret = getattr(config, "WEBHOOK_SECRET_TOKEN", None)

    @app.route(config.WEBHOOK_PATH, methods=["POST"])
    def webhook():
        metrics["requests_total"] += 1
        if request.headers.get("content-type") != "application/json":
            return "", 415
        if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
            return "", 403
        data = request.get_json()
        update = telebot.types.Update.de_json(data)
        bot.process_new_updates([update])
        metrics["updates_total"] += 1
        return ""

    @app.route("/metrics", methods=["GET"])
    def metrics_route():
        return "ok"

    return app
