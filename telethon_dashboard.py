import telebot
from bot_instance import bot
import telethon_manager
from navigation import nav_system
from utils.message_chunker import send_long_message


def show_telethon_dashboard(chat_id, store_id):
    """Send a compact dashboard with Telethon stats and action buttons.

    The stats are pulled from :mod:`telethon_manager` and summarize whether
    the Telethon daemon is active for the given store and how many messages
    were sent.  Navigation relies on :func:`nav_system.create_universal_navigation`
    which injects the standard "Inicio" and "❌ Cancelar" buttons alongside the
    provided quick actions for detecting topics, testing a message send and
    restarting the daemon.
    """

    stats = telethon_manager.get_stats(store_id) or {}
    status = "Activo" if stats.get("active") else "Inactivo"
    sent = stats.get("sent", 0)

    lines = [
        "🤖 *Panel de Telethon*",
        f"Estado: {status}",
        f"Enviados: {sent}",
    ]

    quick_actions = [
        ("🧵 Topics", f"telethon_detect_{store_id}"),
        ("✉️ Prueba", f"telethon_test_{store_id}"),
        ("♻️ Reiniciar", f"telethon_restart_{store_id}"),
    ]

    markup = nav_system.create_universal_navigation(
        chat_id, f"telethon_dashboard_{store_id}", quick_actions
    )
    send_long_message(bot, chat_id, "\n".join(lines), markup=markup, parse_mode="Markdown")
