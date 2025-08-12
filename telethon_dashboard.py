import telebot
from bot_instance import bot
import telethon_manager
import db
from navigation import nav_system
from utils.message_chunker import send_long_message


def show_telethon_dashboard(chat_id, store_id):
    """Send a dashboard with Telethon metrics and helper actions.

    The panel displays basic statistics about the Telethon integration along
    with quick action buttons to manage the daemon.  It also lists the topics
    currently configured for the given store so administrators can quickly
    verify what will be targeted during broadcasts.
    """

    stats = telethon_manager.get_stats(store_id) or {}
    topics = db.get_store_topics(store_id)

    lines = [
        "🤖 *Panel de Telethon*",
        "",
        "*Métricas:*",
        f"🔁 Daemon: {stats.get('daemon', '-')}",
        f"🔌 API: {'OK' if stats.get('api') else 'No'}",
        f"🧵 Topics: {stats.get('topics', 0)}",
        f"📤 Último envío: {stats.get('last_send', '-')}",
        "",
        "*Acciones rápidas:*",
        "- Detectar topics",
        "",
        "*Mantenimiento:*",
        "- Prueba de envío",
        "- Reiniciar daemon",
        "",
        "*Topics configurados:*",
    ]

    if topics:
        for t in topics:
            lines.append(
                f"• {t.get('group_name', '')} ({t.get('topic_id', 0)})"
            )
    else:
        lines.append("Ninguno")

    quick_actions = [
        ("🧵 Topics", f"telethon_detect_{store_id}"),
        ("✉️ Prueba", f"telethon_test_{store_id}"),
        ("♻️ Reiniciar", f"telethon_restart_{store_id}"),
    ]

    markup = nav_system.create_universal_navigation(
        chat_id, f"telethon_dashboard_{store_id}", quick_actions
    )
    send_long_message(bot, chat_id, "\n".join(lines), markup=markup, parse_mode="Markdown")
