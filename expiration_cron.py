#!/usr/bin/env python3
"""Notify users when their purchases expire."""
from datetime import datetime
import os
from dotenv import load_dotenv
import telebot
import db

load_dotenv()

def get_bot():
    token = os.getenv("TELEGRAM_TOKEN")
    if token:
        token = token.split(",")[0].strip()
        if token:
            return telebot.TeleBot(token)
    from bot_instance import bot
    return bot

def main():
    bot = get_bot()
    conn = db.get_db_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute(
        "SELECT id, username, name_good, expires_at FROM purchases WHERE expires_at IS NOT NULL AND expires_at <= ?",
        (now,)
    )
    rows = cur.fetchall()
    for user_id, username, product, expires_at in rows:
        try:
            bot.send_message(
                user_id,
                f"Tu compra de {product} ha expirado. Vuelve a comprar si deseas renovarla."
            )
        except Exception as e:
            print(f"Error notificando a {user_id}: {e}")

if __name__ == "__main__":
    main()
