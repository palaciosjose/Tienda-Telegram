import telebot
from bot_instance import bot
import db
import telethon_manager
import files
import shelve
from utils.message_chunker import send_long_message
from navigation import nav_system


def show_global_telethon_config(chat_id, user_id):
    """Display global Telethon configuration and available actions.

    Parameters
    ----------
    chat_id: int
        Chat where the information will be sent.
    user_id: int
        Administrator requesting the information. Used to scope store
        operations when actions are triggered via callbacks.
    """

    status = db.get_global_telethon_status()
    lines = ["⚙️ *Configuración Global de Telethon*"]
    # Sort keys to keep the output stable for administrators
    for key in sorted(status):
        lines.append(f"{key}: {status[key]}")
    if len(lines) == 1:
        lines.append("Sin configuración")

    actions = [
        ("♻️ Reiniciar", "global_restart_daemons"),
        ("📄 Reporte", "global_generate_report"),
    ]
    markup = nav_system.create_universal_navigation(
        chat_id, "admin_telethon_config", actions
    )
    send_long_message(bot, chat_id, "\n".join(lines), markup=markup, parse_mode="Markdown")


def global_telethon_config(callback_data, chat_id, user_id=None):
    """Handle callbacks for global Telethon configuration actions."""

    if user_id is None:
        user_id = chat_id

    if callback_data in ("admin_telethon_config", "global_telethon_config"):
        show_global_telethon_config(chat_id, user_id)
        return

    stores = db.get_user_stores(user_id)

    if callback_data == "global_restart_daemons":
        lines = []
        for store in stores:
            try:
                telethon_manager.restart_daemon(store["id"])
                lines.append(f"Tienda {store['name']} ({store['id']}): reiniciada")
            except Exception:
                lines.append(f"Tienda {store['name']} ({store['id']}): error")
        if not lines:
            lines.append("No hay tiendas para reiniciar")
        send_long_message(
            bot, chat_id, "♻️ Daemons reiniciados\n" + "\n".join(lines)
        )
    elif callback_data == "global_generate_report":
        report_lines = ["📄 Reporte de Telethon"]
        for store in stores:
            stats = telethon_manager.get_stats(store["id"])
            report_lines.append(
                f"{store['name']} ({store['id']}): activo={stats['active']} enviados={stats['sent']}"
            )
        if len(report_lines) == 1:
            report_lines.append("Sin datos disponibles")
        send_long_message(bot, chat_id, "\n".join(report_lines))


def start_telethon_wizard(chat_id, store_id, action="next"):
    """Execute the Telethon configuration wizard step by step.

    Each invocation advances the wizard for ``chat_id`` one step forward.  The
    current position is persisted in :mod:`shelve` under ``telethon_step`` so the
    process can be resumed later.  A simple text based progress bar is shown to
    the user after each step.
    """

    key = f"{chat_id}_telethon_step"
    total_steps = 3  # detection -> test -> activation

    def _show_progress(current):
        bar = "#" * current + "-" * (total_steps - current)
        send_long_message(bot, chat_id, f"[{bar}] {int(current / total_steps * 100)}%")

    with shelve.open(files.sost_bd) as bd:
        step = bd.get(key, 0)

        status = db.get_global_telethon_status()
        if step == 0:
            if not status.get("api_id") or not status.get("api_hash"):
                send_long_message(
                    bot,
                    chat_id,
                    "Faltan credenciales de Telethon. Configura API ID y API HASH primero.",
                )
                bd[key] = 0
                return

            def progress(msg):
                send_long_message(bot, chat_id, msg)

            summary = telethon_manager.detect_topics(store_id, progress_callback=progress)
            send_long_message(bot, chat_id, summary)
            send_long_message(bot, chat_id, "Seleccionando topics automáticamente...")
            telethon_manager.start_auto_detection(store_id, progress_callback=progress)
            send_long_message(bot, chat_id, "Selección automática completada")

            bd[key] = 1
            _show_progress(1)
            send_long_message(bot, chat_id, "Detección de topics completada. Ejecuta una prueba.")
            return

        if step == 1:
            telethon_manager.test_send(store_id)
            bd[key] = 2
            _show_progress(2)
            send_long_message(bot, chat_id, "Prueba enviada. Activa el servicio.")
            return

        if step >= 2:
            telethon_manager.restart_daemon(store_id)
            _show_progress(3)
            send_long_message(bot, chat_id, "Telethon activado correctamente.")
            if key in bd:
                del bd[key]


def telethon_wizard_callback(callback_data, chat_id):
    """Route wizard-related callbacks."""
    if callback_data.startswith("telethon_start_"):
        store_id = int(callback_data.split("_")[-1])
        start_telethon_wizard(chat_id, store_id)
    elif callback_data == "telethon_help":
        start_telethon_wizard(chat_id, None, action="guide")
    elif callback_data.startswith("telethon_prev_"):
        store_id = int(callback_data.split("_")[-1])
        start_telethon_wizard(chat_id, store_id, action="prev")


def show_telethon_wizard_entry(chat_id, store_id):
    """Display initial wizard entry buttons using universal navigation."""
    actions = [
        ("🚀 Iniciar config", f"telethon_start_{store_id}"),
        ("📖 Guía", "telethon_help"),
    ]
    markup = nav_system.create_universal_navigation(
        chat_id, f"telethon_wizard_{store_id}", store_id, actions
    )
    send_long_message(bot, chat_id, "Configuración de Telethon", markup=markup)

