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
    try:
        daily = db.get_daily_campaign_counts(store_id)
    except Exception:
        daily = {"current": 0, "max": 0}
    try:
        alerts = db.get_alerts(limit=3)
    except Exception:
        alerts = []
    topics = db.get_store_topics(store_id)

    lines = [
        "🤖 *Panel de Telethon*",
        "",
        "*Métricas:*",
        f"📆 Campañas hoy: {daily.get('current', 0)}",
        f"⚡ {daily.get('current', 0)}/{daily.get('max', 0)}",
        f"🔁 Daemon: {stats.get('daemon', '-')}",
        f"⏱️ Conexión: {stats.get('last_activity', '-')}",
        f"🔌 API: {'OK' if stats.get('api') else 'No'}",
        f"🧵 Topics: {stats.get('topics', 0)}",
        f"📤 Último envío: {stats.get('last_send', '-')}",
        "",
        "*Acciones rápidas:*",
        "- Detectar topics",
        "- Prueba de envío",
        "- Reiniciar daemon",
        "",
        "*Mantenimiento:*",
        "- Limpiar sesiones",
        "- Exportar configuración",
        "- Importar configuración",
        "",
        "*Topics configurados:*",
    ]

    if topics:
        for t in topics:
            success = total = 0
            try:
                group_key = f"{t.get('group_id', '')}:{t.get('topic_id', 0)}"
                con = db.get_db_connection()
                cur = con.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM send_logs WHERE platform='telethon' AND shop_id=? AND group_id=?",
                    (store_id, group_key),
                )
                total = cur.fetchone()[0] or 0
                cur.execute(
                    "SELECT COUNT(*) FROM send_logs WHERE platform='telethon' AND status='success' AND shop_id=? AND group_id=?",
                    (store_id, group_key),
                )
                success = cur.fetchone()[0] or 0
            except Exception:
                pass
            lines.append(
                f"• {t.get('group_name', '')} ({t.get('topic_id', 0)}) - {success}/{total}"
            )
    else:
        lines.append("Ninguno")

    lines.extend([
        "",
        "*Alertas recientes:*",
    ])
    if alerts:
        for a in alerts:
            lines.append(f"⚠️ {a.get('message', '')}")
    else:
        lines.append("Sin alertas")

    quick_actions = [
        ("🧵 Topics", f"quick_detect_{store_id}"),
        ("✉️ Prueba", f"quick_test_{store_id}"),
        ("♻️ Reiniciar", f"quick_restart_{store_id}"),
    ]

    markup = nav_system.create_universal_navigation(
        chat_id, f"telethon_dashboard_{store_id}", quick_actions
    )
    send_long_message(bot, chat_id, "\n".join(lines), markup=markup, parse_mode="Markdown")
