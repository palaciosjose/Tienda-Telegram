import telebot, config

_token = config.token or "123:ABC"
try:
    bot = telebot.TeleBot(_token)
except Exception:
    bot = telebot.TeleBot("123:ABC")
