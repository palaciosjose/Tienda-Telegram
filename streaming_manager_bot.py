import telethon_dashboard
import telethon_manager
from bot_instance import bot


class StreamingManagerBot:
    """Router for inline callback queries."""

    def __init__(self, bot_instance=bot):
        self.bot = bot_instance

    def route_callback(self, callback_data, chat_id):
        if callback_data.startswith("telethon_dashboard_"):
            store_id = int(callback_data.rsplit("_", 1)[1])
            telethon_dashboard.show_telethon_dashboard(chat_id, store_id)
        elif callback_data.startswith("telethon_detect_"):
            store_id = int(callback_data.rsplit("_", 1)[1])
            telethon_manager.detect_topics(store_id)
            self.bot.send_message(chat_id, "Detección iniciada")
        elif callback_data.startswith("telethon_test_"):
            store_id = int(callback_data.rsplit("_", 1)[1])
            telethon_manager.test_send(store_id)
            self.bot.send_message(chat_id, "Envío de prueba enviado")
        elif callback_data.startswith("telethon_restart_"):
            store_id = int(callback_data.rsplit("_", 1)[1])
            telethon_manager.restart_daemon(store_id)
            self.bot.send_message(chat_id, "Daemon reiniciado")
