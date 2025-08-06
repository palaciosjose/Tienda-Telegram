import config
from bot_instance import bot
import db


def _check_thresholds():
    """Scan database for conditions that should trigger alerts."""
    con = db.get_db_connection()
    cur = con.cursor()
    db._ensure_shop_extra_columns(cur)
    try:
        cur.execute(
            "SELECT id, name, max_campaigns_daily, current_campaigns_today, telethon_daemon_status FROM shops"
        )
        for sid, name, max_daily, current, daemon_status in cur.fetchall():
            if max_daily and current >= max_daily:
                msg = f"{name} excedió campañas: {current}/{max_daily}"
                db.log_event("ALERT", msg, sid)
                db.add_alert("ALERT", msg)
            if daemon_status and str(daemon_status).lower() == "down":
                msg = f"Daemon caído en {name}"
                db.log_event("ALERT", msg, sid)
                db.add_alert("ALERT", msg)
    except Exception:
        # If shops table doesn't exist or query fails we ignore silently
        pass


def dispatch_alerts():
    """Send pending alerts to the SuperAdmin and store them if delivery fails."""
    _check_thresholds()
    pending = db.get_unsent_alerts()
    if not pending:
        return
    sent_ids = []
    for alert in pending:
        try:
            bot.send_message(
                config.admin_id,
                f"⚠️ {alert['level']}: {alert['message']}"
            )
            sent_ids.append(alert["id"])
        except Exception:
            # If sending fails, keep the alert unsent
            db.log_event("ERROR", f"No se pudo enviar alerta: {alert['message']}")
    db.mark_alerts_sent(sent_ids)
