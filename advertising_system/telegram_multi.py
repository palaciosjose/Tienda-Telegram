import telebot
import time
import random
from threading import Lock

class TelegramMultiBot:
    MAX_CAPTION_LENGTH = 1024

    def __init__(self, tokens):
        self.bots = [telebot.TeleBot(token) for token in tokens]
        self.current_bot = 0
        self.lock = Lock()
        self.rate_limit = 1.0
        self.last_sends = [0] * len(self.bots)

    def get_next_bot(self):
        with self.lock:
            start_bot = self.current_bot
            while True:
                bot_index = self.current_bot
                elapsed = time.time() - self.last_sends[bot_index]
                if elapsed >= self.rate_limit:
                    self.current_bot = (self.current_bot + 1) % len(self.bots)
                    return bot_index
                self.current_bot = (self.current_bot + 1) % len(self.bots)
                if self.current_bot == start_bot:
                    time.sleep(0.1)

    def send_message(self, group_id, message, media_file_id=None, media_type=None, buttons=None, topic_id=None):
        bot_index = self.get_next_bot()
        bot = self.bots[bot_index]
        try:
            markup = None
            if buttons:
                markup = telebot.types.InlineKeyboardMarkup()
                if buttons.get('button1_text'):
                    markup.add(telebot.types.InlineKeyboardButton(buttons['button1_text'], url=buttons['button1_url']))
                if buttons.get('button2_text'):
                    markup.add(telebot.types.InlineKeyboardButton(buttons['button2_text'], url=buttons['button2_url']))
            
            # Parámetros base para el envío
            send_params = {
                'chat_id': group_id,
                'reply_markup': markup
            }
            
            # Agregar topic_id si está especificado
            if topic_id is not None:
                send_params['message_thread_id'] = topic_id
                
            if media_file_id:
                if message and len(message) > self.MAX_CAPTION_LENGTH:
                    message = message[: self.MAX_CAPTION_LENGTH - 1] + "…"
                if media_type == 'photo':
                    bot.send_photo(caption=message, photo=media_file_id, **send_params)
                elif media_type == 'video':
                    bot.send_video(caption=message, video=media_file_id, **send_params)
                elif media_type == 'document':
                    bot.send_document(caption=message, document=media_file_id, **send_params)
                else:
                    send_params['text'] = message
                    send_params['parse_mode'] = 'Markdown'
                    bot.send_message(**send_params)
            else:
                send_params['text'] = message
                send_params['parse_mode'] = 'Markdown'
                bot.send_message(**send_params)
                
            self.last_sends[bot_index] = time.time()
            topic_info = f" (Topic: {topic_id})" if topic_id else " (Grupo principal)"
            return True, f"Enviado exitosamente{topic_info}"
            
        except Exception as e:
            error_msg = str(e)
            if "bot was blocked" in error_msg.lower():
                return False, "Bot bloqueado en el grupo"
            elif "chat not found" in error_msg.lower():
                return False, "Grupo no encontrado"
            elif "topic closed" in error_msg.lower():
                return False, "Topic cerrado o no disponible"
            elif "message_thread_id" in error_msg.lower():
                return False, "Topic ID inválido o grupo sin temas habilitados"
            elif "too many requests" in error_msg.lower():
                time.sleep(random.uniform(5, 10))
                return False, "Rate limit excedido"
            elif "caption is too long" in error_msg.lower():
                return False, "Caption demasiado largo"
            else:
                return False, f"Error: {error_msg}"
