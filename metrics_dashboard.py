import db
from bot_instance import bot
from navigation import nav_system
from utils.message_chunker import send_long_message


def show_global_metrics(chat_id, user_id):
    """Display global ROI, ranking, alerts and Telethon state."""
    if db.get_user_role(user_id) != 'superadmin':
        # Ensure even short warnings go through the chunker for
        # consistent behaviour across the codebase.
        send_long_message(bot, chat_id, '❌ Acceso restringido.')
        return

    metrics = db.get_global_metrics()
    alerts = db.get_alerts()

    lines = [
        '🌐 *Métricas Globales*',
        f"ROI: {metrics.get('roi', 0)}",
        f"Telethon: {metrics.get('telethon_active', 0)}/{metrics.get('telethon_total', 0)} activos",
        '',
        '*Ranking:*',
    ]
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
            ('⚠️ Alertas', 'global_metrics'),
        ],
    )
    send_long_message(bot, chat_id, '\n'.join(lines), markup=key, parse_mode='Markdown')
    db.log_event('INFO', f'user {user_id} viewed global_metrics')


def _global_metrics_nav(chat_id, _store_id=None):
    show_global_metrics(chat_id, chat_id)


nav_system.register('global_metrics', _global_metrics_nav)
