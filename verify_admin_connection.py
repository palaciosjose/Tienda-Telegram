#!/usr/bin/env python3
"""Herramienta de diagnóstico para verificar la conexión con el administrador."""

import telebot
import config
import dop


def main():
    print(f"ID de administrador configurado: {config.admin_id}")
    admin_list = dop.get_adminlist()
    print(f"Lista completa de administradores: {admin_list}")

    bot = telebot.TeleBot(config.token)
    try:
        bot.send_message(config.admin_id, "✅ Conexión de prueba exitosa")
        print("✅ Mensaje enviado correctamente")
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")


if __name__ == "__main__":
    main()
