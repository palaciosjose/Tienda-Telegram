import telebot
from bot_instance import bot
import db
import telethon_manager
import files
import shelve
from utils.message_chunker import send_long_message


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

    # Use send_long_message to respect the 4096 character limit.
    send_long_message(bot, chat_id, "\n".join(lines), parse_mode="Markdown")

    # Inline keyboard with available actions
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(
            text="Reiniciar daemons", callback_data="global_restart_daemons"
        ),
        telebot.types.InlineKeyboardButton(
            text="Generar reporte", callback_data="global_generate_report"
        ),
    )
    send_long_message(bot, chat_id, "Acciones disponibles:", markup=markup)


def global_telethon_config(callback_data, chat_id, user_id=None):
    """Handle callbacks for global Telethon configuration actions."""

    if user_id is None:
        user_id = chat_id

    if callback_data == "admin_telethon_config":
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
    """Guide a user through the Telethon configuration wizard."""
    key = f"{chat_id}_telethon_step"
    if action == "guide":
        guide = (
            "Guía de configuración:\n"
            "1. Credenciales de API.\n"
            "2. Grupo bridge.\n"
            "3. Detección de topics.\n"
            "4. Prueba de envío.\n"
            "5. Activación."
        )
        send_long_message(bot, chat_id, guide)
        return

    with shelve.open(files.sost_bd) as bd:
        step = bd.get(key, 0)
        if action == "prev" and step > 0:
            step -= 1
            bd[key] = step

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
            step = 1
            bd[key] = step
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    text="⬅️ Atrás", callback_data=f"telethon_prev_{store_id}"
                )
            )
            send_long_message(
                bot,
                chat_id,
                "Credenciales OK. Proporciona el ID del grupo bridge.",
                markup=markup,
            )
            return

        if step == 1:
            step = 2
            bd[key] = step
            telethon_manager.detect_topics(store_id)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    text="⬅️ Atrás", callback_data=f"telethon_prev_{store_id}"
                )
            )
            send_long_message(
                bot,
                chat_id,
                "Detección de topics completada. Ejecuta una prueba.",
                markup=markup,
            )
            return

        if step == 2:
            step = 3
            bd[key] = step
            telethon_manager.test_send(store_id)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    text="⬅️ Atrás", callback_data=f"telethon_prev_{store_id}"
                )
            )
            send_long_message(
                bot,
                chat_id,
                "Prueba enviada. Activa el servicio.",
                markup=markup,
            )
            return

        if step == 3:
            telethon_manager.restart_daemon(store_id)
            send_long_message(bot, chat_id, "Telethon activado correctamente.")
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
    """Display initial wizard entry buttons."""
    key = telebot.types.InlineKeyboardMarkup()
    key.add(
        telebot.types.InlineKeyboardButton(
            text="🚀 Iniciar config", callback_data=f"telethon_start_{store_id}"
        ),
        telebot.types.InlineKeyboardButton(
            text="📖 Guía", callback_data="telethon_help"
        ),
    )
    send_long_message(bot, chat_id, "Configuración de Telethon", markup=key)

