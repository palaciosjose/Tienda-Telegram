#!/usr/bin/env python3
import sys
import os

# Añade la carpeta del script al `sys.path` para poder importar los módulos
# del proyecto sin depender de rutas absolutas.
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
import config
from bot_instance import bot
import telebot
import sqlite3
import json
from datetime import datetime, timedelta

def should_send_now(shop_id=1):
    conn = sqlite3.connect('data/db/main_data.db')
    cursor = conn.cursor()
    now = datetime.now()
    current_time = now.strftime('%H:%M')
    current_day = now.strftime('%A').lower()
    english_to_spanish = {
        'monday': 'lunes',
        'tuesday': 'martes',
        'wednesday': 'miercoles',
        'thursday': 'jueves',
        'friday': 'viernes',
        'saturday': 'sabado',
        'sunday': 'domingo',
    }
    time_range = []
    for offset in [-1, 0, 1]:
        time_check = (now + timedelta(minutes=offset)).strftime('%H:%M')
        time_range.append(time_check)
    cursor.execute(
        'SELECT * FROM campaign_schedules WHERE is_active = 1 AND shop_id = ?',
        (shop_id,)
    )
    schedules = cursor.fetchall()
    for schedule in schedules:
        schedule_json = json.loads(schedule[4])
        campaign_id = schedule[1]
        schedule_id = schedule[0]
        last_sent = schedule[7] or ""
        group_ids = schedule[10] or ""  # group_ids está en columna 10
        times = None
        if current_day in schedule_json:
            times = schedule_json[current_day]
        else:
            span_day = english_to_spanish.get(current_day)
            if span_day and span_day in schedule_json:
                times = schedule_json[span_day]

        if times:
            for t in times:
                if t in time_range:
                    today_str = now.strftime('%Y-%m-%d')
                    time_key = f"{today_str} {t}"
                    if time_key in last_sent:
                        print(f"⏳ Ya enviado: {time_key}")
                        continue
                    send_campaign(campaign_id, group_ids)
                    if last_sent:
                        next_send_time = f"{last_sent},{time_key}"
                    else:
                        next_send_time = time_key
                    cursor.execute('UPDATE campaign_schedules SET next_send_telegram = ? WHERE id = ?', (next_send_time, schedule_id))
                    conn.commit()
                    print(f"✅ Marcado como enviado: {time_key}")
                    conn.close()
                    return True
    conn.close()
    return False

def send_campaign(campaign_id, group_ids=""):
    conn = sqlite3.connect('data/db/main_data.db')
    cursor = conn.cursor()
    
    # OBTENER GRUPOS CON TOPICS
    if group_ids:
        # Filtrar por IDs específicos
        ids = [id.strip() for id in group_ids.split(',') if id.strip()]
        placeholders = ','.join(['?' for _ in ids])
        cursor.execute(f'SELECT group_id, topic_id FROM target_groups WHERE status = "active" AND id IN ({placeholders})', ids)
    else:
        # Todos los grupos activos
        cursor.execute('SELECT group_id, topic_id FROM target_groups WHERE status = "active"')
    
    groups = cursor.fetchall()
    cursor.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,))
    campaign = cursor.fetchone()
    
    if campaign and groups:
        campaign_name = campaign[1].replace('Producto ', '')
        cursor.execute('SELECT name, description, price, media_file_id, media_type FROM goods WHERE shop_id = 1 AND name = ?', (campaign_name,))
        product = cursor.fetchone()
        if not product:
            cursor.execute('SELECT name, description, price, media_file_id, media_type FROM goods WHERE shop_id = 1 AND name LIKE ?', (f'%{campaign_name}%',))
            product = cursor.fetchone()
        if product:
            title = f"🛒 {product[0]}"
            message_parts = [title]
            if product[1]:
                message_parts.append(f"📝 {product[1]}")
            if product[2]:
                message_parts.append(f"💰 Precio: ${product[2]}")
            full_message = '\n'.join(message_parts)
            media_file_id = product[3]
            media_type = product[4]
            print(f"✅ USANDO DATOS DE PRODUCTO: {product[0]}")
        else:
            title = campaign[1]
            message_text = campaign[2]
            full_message = f"📢 {title}\n\n{message_text}" if message_text else f"📢 {title}"
            media_file_id = campaign[3]
            media_type = campaign[4]
            print(f"✅ USANDO DATOS DE CAMPAÑA: {title}")
        
        button_text = campaign[6]
        button_url = campaign[7]
        markup = None
        if button_text and button_url:
            markup = telebot.types.InlineKeyboardMarkup()
            button = telebot.types.InlineKeyboardButton(button_text, url=button_url)
            markup.add(button)
        
        for group in groups:
            try:
                group_id = group[0]
                topic_id = group[1] if len(group) > 1 else None
                
                if media_file_id and media_type == 'photo':
                    bot.send_photo(group_id, media_file_id, caption=full_message, reply_markup=markup, message_thread_id=topic_id)
                elif media_file_id and media_type == 'video':
                    bot.send_video(group_id, media_file_id, caption=full_message, reply_markup=markup, message_thread_id=topic_id)
                else:
                    bot.send_message(group_id, full_message, reply_markup=markup, message_thread_id=topic_id)
                
                topic_info = f" Topic {topic_id}" if topic_id else " (grupo principal)"
                if product:
                    print(f'🎉 CAMPAÑA DE PRODUCTO {campaign_id} ENVIADA A {group_id}{topic_info}')
                else:
                    print(f'🎉 CAMPAÑA NORMAL {campaign_id} ENVIADA A {group_id}{topic_info}')
            except Exception as e:
                print(f'❌ Error: {e}')
    conn.close()

def main():
    print(f"AutoSender iniciado: {datetime.now()}")

    shop_id = None
    if len(sys.argv) > 1:
        try:
            shop_id = int(sys.argv[1])
        except ValueError:
            print(f"❌ shop_id invalido: {sys.argv[1]}. Usando valor por defecto")

    if shop_id is None:
        shop_id = int(os.getenv("SHOP_ID", "1"))

    should_send_now(shop_id)

if __name__ == '__main__':
    main()