import db
from bot_instance import bot
from navigation import nav_system
from utils.message_chunker import send_long_message
from utils.ascii_chart import sparkline


def show_global_metrics(chat_id, user_id):
    """Display global ROI, ranking, alerts and Telethon state.

    The returned message uses :func:`nav_system.create_universal_navigation` to
    append the standard navigation buttons ("🏠 Inicio" and "❌ Cancelar") along
    with a few quick actions specific to this dashboard.
    """
    if db.get_user_role(user_id) != 'superadmin':
        # Ensure even short warnings go through the chunker for
        # consistent behaviour across the codebase.
        send_long_message(bot, chat_id, '❌ Acceso restringido.')
        db.log_event('WARNING', f'user {user_id} denied global_metrics')
        return

    metrics = db.get_global_metrics()
    alerts = db.get_alerts()
    sales_ts = db.get_sales_timeseries()
    camp_ts = db.get_campaign_timeseries()

    lines = [
        '🌐 *Métricas Globales*',
        f"ROI: {metrics.get('roi', 0)}",
        f"Telethon: {metrics.get('telethon_active', 0)}/{metrics.get('telethon_total', 0)} activos",
    ]
    if sales_ts:
        vals = [s['total'] for s in sales_ts]
        delta = vals[-1] - (vals[-2] if len(vals) > 1 else 0)
        lines.append(f"💹 Ventas 7d: {sparkline(vals)} ({delta:+})")
    if camp_ts:
        vals = [c['count'] for c in camp_ts]
        delta = vals[-1] - (vals[-2] if len(vals) > 1 else 0)
        lines.append(f"📣 Campañas 7d: {sparkline(vals)} ({delta:+})")

    lines.extend(['', '*Ranking:*'])
    for idx, r in enumerate(metrics.get('ranking', []), 1):
        lines.append(f"{idx}. {r.get('name')} - ${r.get('total')}")

    if alerts:
        lines.append('\n*Alertas recientes:*')
        for a in alerts:
            lines.append(f"{a.get('level')}: {a.get('message')}")
    else:
        lines.append('\n*Alertas recientes:* Ninguna')

    key = nav_system.create_universal_navigation(
        chat_id,
        'global_metrics',
        [
            ('🔄 Actualizar', 'global_metrics'),
            ('📊 Reportes', 'global_metrics'),
            ('⚠️ Alertas', 'global_alerts'),
        ],
    )
    send_long_message(bot, chat_id, '\n'.join(lines), markup=key, parse_mode='Markdown')
    db.log_event('INFO', f'user {user_id} viewed global_metrics')


def _global_metrics_nav(chat_id, _store_id=None):
    show_global_metrics(chat_id, chat_id)


nav_system.register('global_metrics', _global_metrics_nav)


def show_pending_alerts(chat_id, user_id):
    """Display and clear pending alerts for the SuperAdmin."""
    if db.get_user_role(user_id) != 'superadmin':
        send_long_message(bot, chat_id, '❌ Acceso restringido.')
        db.log_event('WARNING', f'user {user_id} denied alerts_view')
        return

    alerts = db.get_alerts(limit=50)
    lines = ['⚠️ *Alertas Pendientes:*']
    if alerts:
        lines.extend(f"{a['level']}: {a['message']}" for a in alerts)
    else:
        lines.append('Ninguna')
    db.clear_alerts()
    key = nav_system.create_universal_navigation(
        chat_id,
        'global_alerts',
        [('⬅️ Volver', 'global_metrics')],
    )
    send_long_message(bot, chat_id, '\n'.join(lines), markup=key, parse_mode='Markdown')


def _global_alerts_nav(chat_id, _store_id=None):
    show_pending_alerts(chat_id, chat_id)


nav_system.register('global_alerts', _global_alerts_nav)
