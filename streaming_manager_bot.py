import telethon_dashboard
import telethon_manager
import telebot
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
            summary = telethon_manager.detect_topics(store_id)
            key = telebot.types.InlineKeyboardMarkup()
            key.add(
                telebot.types.InlineKeyboardButton(
                    text="Seleccionar todos",
                    callback_data=f"start_auto_detection_{store_id}_all",
                ),
                telebot.types.InlineKeyboardButton(
                    text="Personalizar",
                    callback_data=f"start_auto_detection_{store_id}_custom",
                ),
            )
            self.bot.send_message(chat_id, summary, reply_markup=key)
        elif callback_data.startswith("start_auto_detection_"):
            parts = callback_data.split("_")
            store_id = int(parts[3])
            mode = parts[4] if len(parts) > 4 else "all"

            def progress(msg):
                self.bot.send_message(chat_id, msg)

            telethon_manager.start_auto_detection(store_id, mode, progress)
            self.bot.send_message(chat_id, "Configuración confirmada")
        elif callback_data.startswith("telethon_test_"):
            store_id = int(callback_data.rsplit("_", 1)[1])
            telethon_manager.test_send(store_id)
            self.bot.send_message(chat_id, "Envío de prueba enviado")
        elif callback_data.startswith("telethon_restart_"):
            store_id = int(callback_data.rsplit("_", 1)[1])
            telethon_manager.restart_daemon(store_id)
            self.bot.send_message(chat_id, "Daemon reiniciado")
