#!/usr/bin/env python3
import config
import telebot
from flask import Flask, request

app = Flask(__name__)
bot = telebot.TeleBot(config.token)

@app.route('/webhook', methods=['POST'])
def webhook():
    print("🔍 Webhook recibido!")
    try:
        json_str = request.get_data().decode('UTF-8')
        print(f"📥 Datos recibidos: {json_str[:100]}...")
        
        update = telebot.types.Update.de_json(json_str)
        
        if update.message:
            chat_id = update.message.chat.id
            text = update.message.text or "Sin texto"
            
            print(f"💬 Procesando: {text} de {chat_id}")
            
            if text == '/start':
                print("🎯 Comando /start")
                bot.send_message(chat_id, "¡Hola! Bot funcionando perfectamente ✅")
            elif text == '/adm' and chat_id == config.admin_id:
                print("🔧 Comando /adm")
                bot.send_message(chat_id, "🔧 Panel Admin\n✅ Bot activo")
            else:
                print("💭 Mensaje normal")
                bot.send_message(chat_id, f"Recibido: {text}")
        
        return "OK", 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return "Error", 500

if __name__ == '__main__':
    print("🚀 Bot iniciando...")
    app.run(host='0.0.0.0', port=8443, debug=False)
