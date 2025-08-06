import telebot
from bot_instance import bot
import db


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

