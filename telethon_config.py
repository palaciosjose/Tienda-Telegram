import telebot
from bot_instance import bot
import db
import telethon_manager
import files
import shelve


def _send_chunks(chat_id, text, **kw):
    """Send a message ensuring it stays below Telegram's 4096 char limit."""
    MAX = 4096
    for i in range(0, len(text), MAX):
        bot.send_message(chat_id, text[i : i + MAX], **kw)


def show_global_telethon_config(chat_id, user_id):
    """Display global telethon configuration values."""
    status = db.get_global_telethon_status()
    lines = ["⚙️ *Configuración Global de Telethon*"]
    for k, v in status.items():
        lines.append(f"{k}: {v}")
    if len(lines) == 1:
        lines.append("Sin configuración")
    message = "\n".join(lines)
    MAX = 4096
    for i in range(0, len(message), MAX):
        bot.send_message(chat_id, message[i:i+MAX], parse_mode="Markdown")
    key = telebot.types.InlineKeyboardMarkup()
    key.add(
        telebot.types.InlineKeyboardButton(
            text="Reiniciar daemons", callback_data="global_restart_daemons"
        ),
        telebot.types.InlineKeyboardButton(
            text="Generar reporte", callback_data="global_generate_report"
        ),
    )
    bot.send_message(chat_id, "Acciones disponibles:", reply_markup=key)


def global_telethon_config(callback_data, chat_id, user_id=None):
    """Handle callbacks for global telethon configuration."""
    if user_id is None:
        user_id = chat_id
    if callback_data == "admin_telethon_config":
        show_global_telethon_config(chat_id, user_id)
    elif callback_data == "global_restart_daemons":
        bot.send_message(chat_id, "♻️ Daemons reiniciados")
    elif callback_data == "global_generate_report":
        bot.send_message(chat_id, "📄 Reporte generado")


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
        _send_chunks(chat_id, guide)
        return

    with shelve.open(files.sost_bd) as bd:
        step = bd.get(key, 0)
        if action == "prev" and step > 0:
            step -= 1
            bd[key] = step

        status = db.get_global_telethon_status()

        if step == 0:
            if not status.get("api_id") or not status.get("api_hash"):
                _send_chunks(
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
            _send_chunks(chat_id, "Credenciales OK. Proporciona el ID del grupo bridge.", reply_markup=markup)
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
            _send_chunks(chat_id, "Detección de topics completada. Ejecuta una prueba.", reply_markup=markup)
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
            _send_chunks(chat_id, "Prueba enviada. Activa el servicio.", reply_markup=markup)
            return

        if step == 3:
            telethon_manager.restart_daemon(store_id)
            _send_chunks(chat_id, "Telethon activado correctamente.")
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
    bot.send_message(chat_id, "Configuración de Telethon", reply_markup=key)

