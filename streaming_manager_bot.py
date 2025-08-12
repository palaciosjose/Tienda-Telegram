import telethon_dashboard
import telethon_manager
import telebot
from bot_instance import bot
from utils.message_chunker import send_long_message


class StreamingManagerBot:
    """Router for inline callback queries."""

    def __init__(self, bot_instance=bot):
        self.bot = bot_instance
        # Mapping of callback prefixes to handler methods.  This makes it easy
        # to register new quick actions while keeping :meth:`route_callback`
        # concise.
        self.router = {
            "telethon_dashboard": self.quick_dashboard,
            "telethon_detect": self.quick_detect,
            "start_auto_detection": self.quick_start_auto_detection,
            "telethon_test": self.quick_test,
            "telethon_restart": self.quick_restart,
        }

    # --- individual handlers -------------------------------------------------
    def quick_dashboard(self, chat_id, store_id):
        telethon_dashboard.show_telethon_dashboard(chat_id, store_id)

    def quick_detect(self, chat_id, store_id):
        summary = telethon_manager.detect_topics(store_id)
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton(
                text="Seleccionar todos",
                callback_data=f"start_auto_detection_{store_id}_all",
            ),
            telebot.types.InlineKeyboardButton(
                text="Personalizar",
                callback_data=f"start_auto_detection_{store_id}_custom",
            ),
        )
        send_long_message(self.bot, chat_id, summary, markup=markup)

    def quick_start_auto_detection(self, chat_id, store_id, mode):
        def progress(msg):
            send_long_message(self.bot, chat_id, msg)

        telethon_manager.start_auto_detection(store_id, mode, progress)
        send_long_message(self.bot, chat_id, "Configuración confirmada")

    def quick_test(self, chat_id, store_id):
        telethon_manager.test_send(store_id)
        send_long_message(self.bot, chat_id, "Envío de prueba enviado")

    def quick_restart(self, chat_id, store_id):
        telethon_manager.restart_daemon(store_id)
        send_long_message(self.bot, chat_id, "Daemon reiniciado")

    # --- router ---------------------------------------------------------------
    def route_callback(self, callback_data, chat_id):
        """Dispatch callbacks to the appropriate Telethon helper."""

        for prefix, handler in self.router.items():
            if callback_data.startswith(prefix + "_"):
                if prefix == "start_auto_detection":
                    parts = callback_data.split("_")
                    store_id = int(parts[3])
                    mode = parts[4] if len(parts) > 4 else "all"
                    handler(chat_id, store_id, mode)
                else:
                    store_id = int(callback_data.rsplit("_", 1)[1])
                    handler(chat_id, store_id)
                break
