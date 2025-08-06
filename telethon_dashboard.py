import telebot
from bot_instance import bot
import telethon_manager
from navigation import nav_system
from utils.message_chunker import send_long_message


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
    quick_actions = [
        ("Detectar topics", f"telethon_detect_{store_id}"),
        ("Probar envío", f"telethon_test_{store_id}"),
        ("Reiniciar daemon", f"telethon_restart_{store_id}"),
    ]
    key = nav_system.create_universal_navigation(
        chat_id, f"telethon_dashboard_{store_id}", quick_actions
    )
    send_long_message(bot, chat_id, "\n".join(lines), markup=key, parse_mode="Markdown")
