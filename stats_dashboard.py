import db
from bot_instance import bot
from navigation import nav_system
from utils.message_chunker import send_long_message


def show_stats_dashboard(store_id, chat_id):
    """Show an ASCII dashboard with basic sales and user stats."""
    sales = db.get_sales_metrics(store_id) or {}
    users = db.get_user_metrics(store_id) or {}

    box = [
        "+----------+----------+----------+----------+",
        "| Métrica  | Hoy      | Mes      | Total    |",
        "+----------+----------+----------+----------+",
        f"| Ventas   | {('$'+str(sales.get('today',0))).rjust(8)} | {('$'+str(sales.get('month',0))).rjust(8)} | {('$'+str(sales.get('total',0))).rjust(8)} |",
        f"| Usuarios | {str(users.get('today',0)).rjust(8)} | {str(users.get('month',0)).rjust(8)} | {str(users.get('total',0)).rjust(8)} |",
        "+----------+----------+----------+----------+",
    ]

    lines = ["📊 *Estadísticas*", "```", *box, "```"]
    quick_actions = [("📈 Ventas", "stats_sales"), ("👥 Usuarios", "stats_users")]
    markup = nav_system.create_universal_navigation(
        chat_id, f"stats_dashboard_{store_id}", quick_actions
    )
    send_long_message(bot, chat_id, "\n".join(lines), markup=markup, parse_mode="Markdown")


def show_sales_report(chat_id, store_id):
    """Display a simple sales report using timeseries data."""
    ts = db.get_sales_timeseries(store_id)
    lines = ["📈 *Ventas recientes:*"]
    if ts:
        lines.extend(f"{r['day']}: ${r['total']}" for r in ts)
    else:
        lines.append("Sin datos")
    markup = nav_system.create_universal_navigation(
        chat_id, f"stats_sales_{store_id}"
    )
    send_long_message(bot, chat_id, "\n".join(lines), markup=markup, parse_mode="Markdown")


def show_users_report(chat_id, store_id):
    """Display a simple user activity report."""
    ts = db.get_user_timeseries(store_id)
    lines = ["👥 *Usuarios recientes:*"]
    if ts:
        lines.extend(f"{r['day']}: {r['users']}" for r in ts)
    else:
        lines.append("Sin datos")
    markup = nav_system.create_universal_navigation(
        chat_id, f"stats_users_{store_id}"
    )
    send_long_message(bot, chat_id, "\n".join(lines), markup=markup, parse_mode="Markdown")


# Register callbacks for quick navigation
nav_system.register('stats_sales', show_sales_report)
nav_system.register('stats_users', show_users_report)
