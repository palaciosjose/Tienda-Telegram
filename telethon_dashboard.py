import telebot
from bot_instance import bot
import telethon_manager


def show_telethon_dashboard(chat_id, store_id):
    """Display telethon operational stats and action buttons."""
    stats = telethon_manager.get_stats(store_id)
    status = "Activo" if stats.get("active") else "Inactivo"
    sent = stats.get("sent", 0)
    lines = [
        "🤖 *Panel de Telethon*",
        f"Estado: {status}",
        f"Enviados: {sent}",
    ]
    key = telebot.types.InlineKeyboardMarkup()
    key.add(
        telebot.types.InlineKeyboardButton(
            text="Detectar topics", callback_data=f"telethon_detect_{store_id}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Probar envío", callback_data=f"telethon_test_{store_id}"
        ),
    )
    key.add(
        telebot.types.InlineKeyboardButton(
            text="Reiniciar daemon", callback_data=f"telethon_restart_{store_id}"
        )
    )
    bot.send_message(chat_id, "\n".join(lines), reply_markup=key, parse_mode="Markdown")
