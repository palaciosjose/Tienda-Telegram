import telebot, sqlite3, shelve, os, json, re
import config, dop, files
import db
import telethon_config
import datetime
from advertising_system.admin_integration import (
    manager as advertising,
    set_shop_id,
    create_campaign_from_admin,
    list_campaigns_for_admin,
    add_target_group_from_admin,
    get_admin_telegram_groups,
)
from bot_instance import bot
from advertising_system.scheduler import CampaignScheduler
import logging

logging.basicConfig(level=logging.INFO)


def set_state(chat_id, state, prev='main'):
    """Store user state and previous menu"""
    with shelve.open(files.sost_bd) as bd:
        bd[str(chat_id)] = state
        bd[f"{chat_id}_prev"] = prev


def clear_state(chat_id):
    """Remove stored state"""
    with shelve.open(files.sost_bd) as bd:
        if str(chat_id) in bd:
            del bd[str(chat_id)]
        key = f"{chat_id}_prev"
        if key in bd:
            del bd[key]


def cancel_and_reset(chat_id):
    """Clear user state and notify cancellation"""
    clear_state(chat_id)
    bot.send_message(chat_id, '❌ Operación cancelada.')


def get_prev(chat_id):
    with shelve.open(files.sost_bd) as bd:
        return bd.get(f"{chat_id}_prev", 'main')


def route_cancel(chat_id, prev):
    if prev == 'marketing':
        show_marketing_menu(chat_id)
    elif prev == 'discount':
        show_discount_menu(chat_id)
    elif prev == 'product':
        show_product_menu(chat_id)
    elif prev == 'other':
        in_adminka(chat_id, '⚙️ Otros', None, None)
    else:
        in_adminka(chat_id, 'Volver al menú principal', None, None)




def session_expired(chat_id):
    """Informar al usuario que la sesión expiró y volver al menú principal"""
    bot.send_message(chat_id, '❌ La sesión anterior se perdió.')
    with shelve.open(files.sost_bd) as bd:
        if str(chat_id) in bd:
            del bd[str(chat_id)]
    in_adminka(chat_id, 'Volver al menú principal', None, None)


def show_discount_menu(chat_id):
    """Mostrar menú de configuración de descuentos"""
    shop_id = dop.get_shop_id(chat_id)
    config_dis = dop.get_discount_config(shop_id)

    status = 'Activado ✅' if config_dis['enabled'] else 'Desactivado ❌'
    show_fake = 'Sí' if config_dis['show_fake_price'] else 'No'

    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
    toggle = 'Desactivar descuentos' if config_dis['enabled'] else 'Activar descuentos'
    toggle_fake = 'Ocultar precios tachados' if config_dis['show_fake_price'] else 'Mostrar precios tachados'
    user_markup.row(toggle)
    user_markup.row('Cambiar texto', 'Cambiar porcentaje')
    user_markup.row(toggle_fake)
    user_markup.row('Nuevo descuento')
    user_markup.row('Vista previa', 'Volver al menú principal')

    message = (
        f"💸 *Configuración de Descuentos*\n\n"
        f"Estado: {status}\n"
        f"Texto: {config_dis['text']}\n"
        f"Multiplicador: x{config_dis['multiplier']}\n"
        f"Mostrar precios tachados: {show_fake}"
    )

    bot.send_message(chat_id, message, reply_markup=user_markup, parse_mode='Markdown')


def show_product_menu(chat_id):
    """Mostrar listado de productos para la gestión de unidades"""
    con = db.get_db_connection()
    cursor = con.cursor()
    shop_id = dop.get_shop_id(chat_id)
    cursor.execute("SELECT name FROM goods WHERE shop_id = ?;", (shop_id,))
    user_markup = telebot.types.ReplyKeyboardMarkup(True, True)
    count = 0
    for (name,) in cursor.fetchall():
        count += 1
        user_markup.row(name)
    user_markup.row('Volver al menú principal')

    if count == 0:
        bot.send_message(chat_id, '¡No se ha creado ninguna posición todavía!', reply_markup=user_markup)
    else:
        bot.send_message(chat_id, '¿De qué posición desea gestionar unidades?', reply_markup=user_markup, parse_mode='MarkDown')
        with shelve.open(files.sost_bd) as bd:
            bd[str(chat_id)] = 10


def show_marketing_menu(chat_id):
    """Mostrar menú principal de marketing"""
    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
    user_markup.row('🎯 Nueva campaña', '📋 Ver campañas')
    user_markup.row('🛒 Campaña de producto')
    user_markup.row('🗑️ Eliminar campaña')
    user_markup.row('⏰ Programar envíos', '📆 Programaciones')
    user_markup.row('🎯 Gestionar grupos')
    user_markup.row('📊 Estadísticas hoy', '⚙️ Configuración')
    user_markup.row('▶️ Envío manual', 'Volver al menú principal')

    today_stats = advertising.get_today_stats()
    stats_text = (
        f"📢 **Sistema de Marketing**\n\n"
        f"📊 **Estadísticas de hoy:**\n"
        f"- Mensajes enviados: {today_stats['sent']}\n"
        f"- Tasa de éxito: {today_stats['success_rate']}%\n"
        f"- Grupos alcanzados: {today_stats['groups']}\n\n"
        "Selecciona una opción:"
    )

    bot.send_message(chat_id, stats_text, reply_markup=user_markup, parse_mode='Markdown')


def show_superadmin_dashboard(chat_id, user_id):
    """Mostrar panel principal del super admin con información de tiendas."""
    if user_id != config.admin_id:
        bot.send_message(chat_id, '❌ Acceso restringido.')
        return

    con = db.get_db_connection()
    cur = con.cursor()
    try:
        cur.execute('SELECT id, name FROM shops ORDER BY id')
        shops = cur.fetchall()
    except Exception:
        shops = []

    header = '+----+--------------------+----------+--------------+'
    lines = [
        header,
        '| ID | Tienda             | Telethon | Ventas (u/$) |',
        header,
    ]
    for sid, name in shops:
        try:
            cur.execute(
                "SELECT is_active FROM platform_config WHERE platform='telethon' AND shop_id=?",
                (sid,),
            )
            row = cur.fetchone()
            tele_active = bool(row[0]) if row else False
        except Exception:
            tele_active = False
        tele_txt = '✅' if tele_active else '❌'

        try:
            cur.execute(
                "SELECT COUNT(*), COALESCE(SUM(price),0) FROM purchases WHERE shop_id=?",
                (sid,),
            )
            count, total = cur.fetchone()
        except Exception:
            count, total = 0, 0

        lines.append(
            f"| {sid:<2} | {name:<18} | {tele_txt:^8} | {count:>3}/{total or 0:<7} |"
        )

    lines.append(header)
    table = '\n'.join(lines)

    MAX = 4096
    for i in range(0, len(table), MAX):
        bot.send_message(chat_id, table[i:i+MAX])

    key = telebot.types.InlineKeyboardMarkup()
    key.add(
        telebot.types.InlineKeyboardButton(text='Ver todas las tiendas', callback_data='admin_list_shops'),
        telebot.types.InlineKeyboardButton(text='Crear nueva', callback_data='admin_create_shop'),
        telebot.types.InlineKeyboardButton(text='Config Telethon global', callback_data='admin_telethon_config'),
    )
    bot.send_message(chat_id, 'Opciones de gestión:', reply_markup=key)


def finalize_product_campaign(chat_id, shop_id, product):
    """Crear campaña de producto usando la información almacenada."""
    info = dop.get_product_full_info(product, shop_id)
    if not info:
        bot.send_message(chat_id, '❌ Producto no encontrado.')
        return

    text = info['description'] or ''
    if info.get('additional_description'):
        extra = info['additional_description']
        if extra:
            text += ('\n' if text else '') + extra

    media = dop.get_product_media(product, shop_id)
    media_file_id = media['file_id'] if media else None
    media_type = media['type'] if media else None

    data = {
        'name': f'Producto {product}',
        'message_text': text,
        'media_file_id': media_file_id,
        'media_type': media_type,
        'button1_text': 'Ver producto',
        'button1_url': dop.get_product_link(product, shop_id),
        'created_by': chat_id,
    }
    ok, msg = create_campaign_from_admin(data)
    bot.send_message(chat_id, ('✅ ' if ok else '❌ ') + msg)
    with shelve.open(files.sost_bd) as bd:
        if str(chat_id) in bd:
            del bd[str(chat_id)]
    show_marketing_menu(chat_id)


def in_adminka(chat_id, message_text, username, name_user):
    if chat_id in dop.get_adminlist():
        logging.debug("Admin %s selected option: %s", chat_id, message_text)
        shop_id = dop.get_shop_id(chat_id)
        set_shop_id(shop_id)
        normalized = message_text.strip().lower()
        if normalized in ('volver al menú principal', 'volver al menu principal', '/adm'):
            if dop.get_sost(chat_id) is True:
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            if chat_id == config.admin_id:
                user_markup.row('💬 Respuestas')
            user_markup.row('📦 Surtido', '➕ Producto')
            user_markup.row('💰 Pagos')
            user_markup.row('📊 Stats', '📣 Difusión')
            user_markup.row('Resumen de compradores')
            user_markup.row('📢 Marketing')
            user_markup.row('🏷️ Categorías')
            user_markup.row('💸 Descuentos')
            user_markup.row('⚙️ Otros')
            bot.send_message(chat_id, '¡Has ingresado al panel de administración del bot!\nPara salir, presiona /start', reply_markup=user_markup)

        elif message_text == '💬 Respuestas':
            if chat_id != config.admin_id:
                bot.send_message(chat_id, '❌ Solo el super admin puede modificar las respuestas.')
                return
            if dop.check_message('after_buy'):
                after_buy = 'Cambiar'
            else:
                after_buy = 'Añadir'
            if dop.check_message('help'):
                help ='Cambiar'
            else:
                help = 'Añadir'
            if dop.check_message('userfalse'):
                userfalse = 'Cambiar'
            else:
                userfalse = 'Añadir'
            user_markup = telebot.types.ReplyKeyboardMarkup(True, True)
            user_markup.row(after_buy + ' mensaje después de pagar el producto')
            user_markup.row(help + ' respuesta al comando help', userfalse + ' mensaje si no hay nombre de usuario')
            user_markup.row('Agregar/Cambiar mensaje de entrega manual')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, 'Seleccione qué mensaje desea cambiar.\nDespués de seleccionar, recibirá una breve instrucción', reply_markup=user_markup)

        elif 'mensaje después de pagar el producto' in message_text:
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, '¡Ingrese un nuevo mensaje que el bot enviará al usuario después de la compra! En el texto puede usar las palabras `username` y `name`. Se reemplazarán automáticamente por el nombre de usuario', parse_mode='MarkDown', reply_markup=key)
            with open('data/Temp/' + str(chat_id) + '.txt', 'w', encoding='utf-8') as f:
                f.write('after_buy')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 1

        elif 'respuesta al comando help' in message_text:
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, '¡Ingrese un nuevo mensaje de ayuda! En principio, puede poner cualquier cosa allí. En el texto puede usar las palabras `username` y `name`. Se reemplazarán automáticamente por el nombre de usuario', parse_mode='MarkDown', reply_markup=key)
            with open('data/Temp/' + str(chat_id) + '.txt', 'w', encoding='utf-8') as f:
                f.write('help')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 1

        elif 'mensaje si no hay nombre de usuario' in message_text:
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, '¡Ingrese un nuevo mensaje que se enviará si el usuario no tiene `username`! En el texto puede usar `uname`. Se reemplazará automáticamente por el nombre de usuario', parse_mode='MarkDown', reply_markup=key)
            with open('data/Temp/' + str(chat_id) + '.txt', 'w', encoding='utf-8') as f:
                f.write('userfalse')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 1

        elif 'mensaje de entrega manual' in message_text:
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Ingrese el mensaje que recibirá el comprador para productos de entrega manual. Puede usar `username` y `name`.', parse_mode='MarkDown', reply_markup=key)
            with open('data/Temp/' + str(chat_id) + '.txt', 'w', encoding='utf-8') as f:
                f.write('manual_delivery')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 1

        elif '📦 Surtido' == message_text:
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
            user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
            user_markup.row('Cambiar categoría')
            user_markup.row('📝 Descripción adicional')
            user_markup.row('🎬 Multimedia productos')
            user_markup.row('Volver al menú principal')

            con = db.get_db_connection()
            cursor = con.cursor()
            goodz = 'Productos creados:\n\n'
            a = 0
            cursor.execute(
                "SELECT name, description, format, minimum, price, stored, duration_days FROM goods WHERE shop_id = ?;",
                (shop_id,)
            )
            for name, description, format, minimum, price, stored, duration in cursor.fetchall():
                a += 1
                amount = dop.amount_of_goods(name, shop_id)
                dur_line = f"\n*Duración:* {duration} días" if duration not in (None, 0) else ''
                goodz += (
                    '*Nombre:* ' + name + '\n*Descripción:* ' + description[:50] + "..." +
                    '\n*Formato del producto:* ' + format +
                    '\n*Cantidad mínima para comprar:* ' + str(minimum) +
                    '\n*Precio por unidad:* $' + str(price) + ' USD' +
                    dur_line +
                    '\n*Unidades restantes:* ' + str(amount) + '\n\n'
                )
            if a == 0: 
                goodz = '¡No se han creado posiciones todavía!'
            bot.send_message(chat_id, goodz, reply_markup=user_markup, parse_mode='MarkDown')

        elif 'Añadir nueva posición en el escaparate' == message_text:
            key = telebot.types.InlineKeyboardMarkup()
            key.add(
                telebot.types.InlineKeyboardButton(
                    text='Omitir', callback_data='SKIP_NEW_MEDIA'
                )
            )
            key.add(
                telebot.types.InlineKeyboardButton(
                    text='Cancelar y volver al menú principal de administración',
                    callback_data='Volver al menú principal de administración'
                )
            )
            bot.send_message(
                chat_id,
                'Envíe una imagen o video para el producto (opcional) o presione "Omitir"',
                reply_markup=key
            )
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 200

        elif 'Eliminar posición' == message_text:
            con = db.get_db_connection()
            cursor = con.cursor()
            cursor.execute("SELECT name FROM goods WHERE shop_id = ?;", (shop_id,))
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False) 
            a = 0
            for name in cursor.fetchall():
                a += 1
                user_markup.row(name[0])
            if a == 0: 
                user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
                user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
                user_markup.row('Cambiar categoría')
                user_markup.row('📝 Descripción adicional')
                user_markup.row('🎬 Multimedia productos')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¡No se ha creado ninguna posición todavía!', reply_markup=user_markup)
            else:
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¿Qué posición desea eliminar?', reply_markup=user_markup)
                with shelve.open(files.sost_bd) as bd: 
                    bd[str(chat_id)] = 6

        elif 'Cambiar descripción de posición' == message_text:
            con = db.get_db_connection()
            cursor = con.cursor()
            cursor.execute("SELECT name FROM goods WHERE shop_id = ?;", (shop_id,))
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False) 
            a = 0
            for name in cursor.fetchall():
                a += 1
                user_markup.row(name[0])
            if a == 0: 
                user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
                user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
                user_markup.row('Cambiar categoría')
                user_markup.row('📝 Descripción adicional')
                user_markup.row('🎬 Multimedia productos')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¡No se ha creado ninguna posición todavía!', reply_markup=user_markup)
            else:
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¿Para qué posición desea cambiar la descripción?', reply_markup=user_markup)
                with shelve.open(files.sost_bd) as bd: 
                    bd[str(chat_id)] = 7

        elif 'Cambiar precio' == message_text:
            con = db.get_db_connection()
            cursor = con.cursor()
            cursor.execute("SELECT name FROM goods WHERE shop_id = ?;", (shop_id,))
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False) 
            a = 0
            for name in cursor.fetchall():
                a += 1
                user_markup.row(name[0])
            if a == 0: 
                user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
                user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
                user_markup.row('Cambiar categoría')
                user_markup.row('📝 Descripción adicional')
                user_markup.row('🎬 Multimedia productos')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¡No se ha creado ninguna posición todavía!', reply_markup=user_markup)
            else:
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¿Para qué posición desea cambiar el precio?', parse_mode='Markdown', reply_markup=user_markup)
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 9

        elif 'Cambiar categoría' == message_text:
            con = db.get_db_connection()
            cursor = con.cursor()
            cursor.execute("SELECT name FROM goods WHERE shop_id = ?;", (shop_id,))
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            a = 0
            for name in cursor.fetchall():
                a += 1
                user_markup.row(name[0])
            if a == 0:
                user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
                user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
                user_markup.row('Cambiar categoría')
                user_markup.row('📝 Descripción adicional')
                user_markup.row('🎬 Multimedia productos')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¡No se ha creado ninguna posición todavía!', reply_markup=user_markup)
            else:
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¿Para qué producto desea cambiar la categoría?', reply_markup=user_markup)
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 64

        elif '📝 Descripción adicional' == message_text:
            con = db.get_db_connection()
            cursor = con.cursor()
            cursor.execute("SELECT name FROM goods WHERE shop_id = ?;", (shop_id,))
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False) 
            a = 0
            for name in cursor.fetchall():
                a += 1
                user_markup.row(name[0])
            if a == 0: 
                user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
                user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
                user_markup.row('Cambiar categoría')
                user_markup.row('📝 Descripción adicional')
                user_markup.row('🎬 Multimedia productos')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¡No se ha creado ninguna posición todavía!', reply_markup=user_markup)
            else:
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¿Para qué producto desea editar la descripción adicional?', reply_markup=user_markup)
                with shelve.open(files.sost_bd) as bd: 
                    bd[str(chat_id)] = 28

        elif '🎬 Multimedia productos' == message_text:
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row('📤 Agregar o cambiar multimedia', '🗑️ Eliminar multimedia')
            user_markup.row('📋 Ver productos con multimedia')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, '🎬 **Gestión de Multimedia**\n\nSelecciona una opción:', reply_markup=user_markup, parse_mode='Markdown')

        elif '📤 Agregar o cambiar multimedia' == message_text:
            products = dop.get_goods(shop_id)
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            if not products:
                user_markup.row('🎬 Multimedia productos')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¡No se ha creado ninguna posición todavía!', reply_markup=user_markup)
            else:
                products_with_media = {name: mtype for name, mtype in dop.get_products_with_media(shop_id)}
                emoji_map = {'photo': '📸', 'video': '🎥', 'document': '📄', 'audio': '🎵'}
                for product in products:
                    if product in products_with_media:
                        emoji = emoji_map.get(products_with_media[product], '📎')
                        user_markup.row(f"{emoji} {product}")
                    else:
                        user_markup.row(product)
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '📤 **Agregar o cambiar Multimedia**\n\n¿A qué producto deseas agregar o cambiar multimedia?', reply_markup=user_markup, parse_mode='Markdown')
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 30

        elif '🗑️ Eliminar multimedia' == message_text:
            products_with_media = dop.get_products_with_media(shop_id)
            if not products_with_media:
                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                user_markup.row('🎬 Multimedia productos')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, 'ℹ️ No hay productos con multimedia asignada', reply_markup=user_markup)
            else:
                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                for product, media_type in products_with_media:
                    media_emoji = {'photo': '📸', 'video': '🎥', 'document': '📄', 'audio': '🎵'}.get(media_type, '📎')
                    user_markup.row(f"{media_emoji} {product}")
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '🗑️ **Eliminar Multimedia**\n\n¿De qué producto deseas eliminar multimedia?', reply_markup=user_markup, parse_mode='Markdown')
                with shelve.open(files.sost_bd) as bd: 
                    bd[str(chat_id)] = 31

        elif '📋 Ver productos con multimedia' == message_text:
            products_with_media = dop.get_products_with_media(shop_id)
            menu_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            menu_markup.row('🎬 Multimedia productos')
            menu_markup.row('Volver al menú principal')

            if not products_with_media:
                bot.send_message(
                    chat_id,
                    'ℹ️ No hay productos con multimedia asignada',
                    reply_markup=menu_markup,
                )
            else:
                for product_name, media_type in products_with_media:
                    media_info = dop.get_product_media(product_name, shop_id)
                    caption = dop.format_product_with_media(product_name, shop_id)
                    if media_info:
                        mtype = media_info['type']
                        file_id = media_info['file_id']
                        if mtype == 'photo':
                            bot.send_photo(chat_id, file_id, caption=caption, parse_mode='Markdown')
                        elif mtype == 'video':
                            bot.send_video(chat_id, file_id, caption=caption, parse_mode='Markdown')
                        elif mtype == 'document':
                            bot.send_document(chat_id, file_id, caption=caption, parse_mode='Markdown')
                        elif mtype == 'audio':
                            bot.send_audio(chat_id, file_id, caption=caption, parse_mode='Markdown')
                        elif mtype == 'animation':
                            bot.send_animation(chat_id, file_id, caption=caption, parse_mode='Markdown')
                        else:
                            bot.send_message(chat_id, caption, parse_mode='Markdown')
                    else:
                        bot.send_message(chat_id, caption or product_name, parse_mode='Markdown')

                bot.send_message(
                    chat_id,
                    '📋 Fin de la lista de productos con multimedia',
                    reply_markup=menu_markup,
                )

        elif '➕ Producto' == message_text:
            overview_lines = dop.get_stock_overview()
            if overview_lines:
                step = 10
                for i in range(0, len(overview_lines), step):
                    part = '\n'.join(overview_lines[i:i + step])
                    bot.send_message(chat_id, part, parse_mode='Markdown')
            show_product_menu(chat_id)

        elif '💰 Pagos' == message_text:
            with shelve.open(files.payments_bd) as bd:
                paypal = bd.get('paypal', '❌')
                binance = bd.get('binance', '❌')
            
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row(f'PayPal {paypal}', f'Binance {binance}')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, 'Configuración de métodos de pago:', reply_markup=user_markup)

        elif 'PayPal' in message_text:
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Ingrese el Client ID de PayPal:', reply_markup=key)
            with shelve.open(files.sost_bd) as bd: 
                bd[str(chat_id)] = 18

        elif 'Binance' in message_text:
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Ingrese la API Key de Binance:', reply_markup=key)
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 19

        elif '📊 Stats' == message_text:
            result = dop.get_daily_sales()
            bot.send_message(chat_id, result, parse_mode='Markdown')

        elif 'Resumen de compradores' == message_text:
            lines = dop.get_buyers_summary(shop_id)
            if not lines:
                bot.send_message(chat_id, 'No hay compras registradas.')
            else:
                step = 10
                for i in range(0, len(lines), step):
                    part = '\n'.join(lines[i:i + step])
                    bot.send_message(chat_id, part)

        elif '📣 Difusión' == message_text:
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row('A todos los usuarios', 'Solo a compradores')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, 'Seleccione a qué grupo de usuarios desea enviar el boletín', reply_markup=user_markup)

        elif '📢 Marketing' == message_text:
            show_marketing_menu(chat_id)

        elif '🏷️ Categorías' == message_text:
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row('Añadir categoría', 'Eliminar categoría')
            user_markup.row('Renombrar categoría')
            user_markup.row('Ver categorías')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, 'Gestión de categorías', reply_markup=user_markup)

        elif 'Añadir categoría' == message_text:
            key = telebot.types.ReplyKeyboardMarkup(True, False)
            key.row('Cancelar')
            bot.send_message(chat_id, 'Ingrese el nombre de la nueva categoría:', reply_markup=key)
            set_state(chat_id, 61, 'main')

        elif 'Eliminar categoría' == message_text:
            cats = dop.list_categories(shop_id)
            if not cats:
                bot.send_message(chat_id, 'No existen categorías para eliminar.')
            else:
                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                for _cid, cname in cats:
                    user_markup.row(cname)
                user_markup.row('Cancelar')
                bot.send_message(chat_id, 'Seleccione la categoría a eliminar:', reply_markup=user_markup)
            set_state(chat_id, 60, 'main')

        elif '💸 Descuentos' == message_text:
            show_discount_menu(chat_id)

        elif message_text in ('Desactivar descuentos', 'Activar descuentos'):
            enable = message_text == 'Activar descuentos'
            if dop.update_discount_config(enabled=enable, shop_id=shop_id):
                status = 'activados' if enable else 'desactivados'
                bot.send_message(chat_id, f'✅ Descuentos {status}')
            else:
                bot.send_message(chat_id, '❌ Error actualizando estado')
            show_discount_menu(chat_id)

        elif message_text == 'Cambiar texto':
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='GLOBAL_CANCEL'))
            bot.send_message(chat_id, 'Envíe el nuevo texto de descuento:', reply_markup=key)
            set_state(chat_id, 33, 'discount')

        elif message_text == 'Cambiar porcentaje':
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='GLOBAL_CANCEL'))
            bot.send_message(chat_id, 'Envíe el nuevo porcentaje de descuento:', reply_markup=key)
            set_state(chat_id, 34, 'discount')

        elif message_text in ('Ocultar precios tachados', 'Mostrar precios tachados'):
            show = message_text == 'Mostrar precios tachados'
            if dop.update_discount_config(show_fake_price=show, shop_id=shop_id):
                msg = 'Mostrando precios tachados' if show else 'Ocultando precios tachados'
                bot.send_message(chat_id, f'✅ {msg}')
            else:
                bot.send_message(chat_id, '❌ Error actualizando configuración')
            show_discount_menu(chat_id)

        elif 'Nuevo descuento' == message_text:
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='GLOBAL_CANCEL'))
            bot.send_message(chat_id, 'Ingrese porcentaje de descuento:', reply_markup=key)
            set_state(chat_id, 71, 'discount')

        elif 'Renombrar categoría' == message_text:
            cats = dop.list_categories(shop_id)
            if not cats:
                bot.send_message(chat_id, 'No hay categorías para renombrar.')
            else:
                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                for _cid, cname in cats:
                    user_markup.row(cname)
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, 'Seleccione la categoría a renombrar:', reply_markup=user_markup)
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 63

        elif 'Ver categorías' == message_text:
            cats = dop.list_categories(shop_id)
            if not cats:
                bot.send_message(chat_id, 'No hay categorías registradas.')
            else:
                text = '*Categorías:*\n' + '\n'.join(f'- {c[1]}' for c in cats)
                bot.send_message(chat_id, text, parse_mode='Markdown')

        elif '🎯 Nueva campaña' == message_text:
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, '📝 *Nombre de la campaña*\n\nEnvía el nombre para la nueva campaña:', reply_markup=key, parse_mode='Markdown')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 160

        elif '🛒 Campaña de producto' == message_text:
            goods = dop.get_goods(shop_id)
            if not goods:
                bot.send_message(chat_id, 'No hay productos disponibles.')
            else:
                markup = telebot.types.ReplyKeyboardMarkup(True, False)
                for g in goods:
                    markup.row(g)
                markup.row('Cancelar')
                bot.send_message(chat_id, 'Seleccione el producto para la campaña:', reply_markup=markup)
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 190

        elif '📋 Ver campañas' == message_text:
            campaigns = advertising.get_all_campaigns()
            if not campaigns:
                bot.send_message(chat_id, 'ℹ️ No hay campañas registradas.')
            else:
                markup = telebot.types.InlineKeyboardMarkup()
                lines = ['📋 *Campañas registradas:*']
                for camp in campaigns:
                    lines.append(f"- {camp['id']} {camp['name']} ({camp['status']})")
                    markup.add(
                        telebot.types.InlineKeyboardButton(
                            text=f'✏️ Editar {camp["id"]}',
                            callback_data=f'EDIT_CAMPAIGN_{camp["id"]}'
                        )
                    )
                bot.send_message(
                    chat_id,
                    '\n'.join(lines),
                    reply_markup=markup,
                    parse_mode='Markdown'
                )

        elif '🗑️ Eliminar campaña' == message_text:
            campaigns = advertising.get_all_campaigns()
            if not campaigns:
                bot.send_message(chat_id, 'ℹ️ No hay campañas registradas.')
            else:
                key = telebot.types.InlineKeyboardMarkup()
                key.add(
                    telebot.types.InlineKeyboardButton(
                        text='Cancelar y volver a Marketing',
                        callback_data='Volver a Marketing'
                    )
                )
                lines = ['🗑️ *Eliminar campaña*', '', 'Envía el ID de la campaña a eliminar:', '']
                for camp in campaigns:
                    lines.append(f"- {camp['id']} {camp['name']} ({camp['status']})")
                bot.send_message(chat_id, '\n'.join(lines), reply_markup=key, parse_mode='Markdown')
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 168

        elif message_text.startswith('⏰ Programar envíos'):
            params = message_text.replace('⏰ Programar envíos', '').strip()
            if not params:
                bot.send_message(chat_id, 'Uso: ⏰ Programar envíos <ID> <dias> <HH:MM> <HH:MM>')
            else:
                parts = params.split()
                if len(parts) < 4:
                    bot.send_message(chat_id, 'Uso: ⏰ Programar envíos <ID> <dias> <HH:MM> <HH:MM>')
                else:
                    try:
                        camp_id = int(parts[0])
                        days = parts[1].split(',')
                        times = parts[2:4]
                    except ValueError:
                        cancel_and_reset(chat_id)
                        return

                    groups = advertising.get_target_groups()
                    if not groups:
                        ok, msg = advertising.schedule_campaign(camp_id, days, times)
                        bot.send_message(chat_id, ('✅ ' if ok else '❌ ') + msg)
                    else:
                        markup = telebot.types.ReplyKeyboardMarkup(True, False)
                        for g in groups:
                            title = g['group_name'] or g['group_id']
                            label = f"{title} ({g['id']})"
                            if g.get('topic_id') is not None:
                                label += f" (topic {g['topic_id']})"
                            markup.row(label)
                        markup.row('Todos', 'Cancelar')

                        os.makedirs('data/Temp', exist_ok=True)
                        tmp = f'data/Temp/{chat_id}_schedule.json'
                        with open(tmp, 'w', encoding='utf-8') as f:
                            json.dump({'type': 'create', 'camp_id': camp_id, 'days': days, 'times': times, 'groups': groups}, f)

                        bot.send_message(chat_id, 'Seleccione los grupos destino (enviar IDs separados por coma o "Todos"):', reply_markup=markup)
                        set_state(chat_id, 187, 'marketing')

        elif '📆 Programaciones' == message_text:
            conn = db.get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """SELECT id, group_id, group_name, topic_id
                   FROM target_groups WHERE shop_id = ?""",
                (shop_id,),
            )
            group_rows = cur.fetchall()
            group_map = {
                r[0]: {
                    'group_id': r[1],
                    'group_name': r[2],
                    'topic_id': r[3],
                }
                for r in group_rows
            }

            cur.execute(
                """SELECT cs.id, c.name, cs.is_active, cs.group_ids,
                          cs.frequency, cs.schedule_json, cs.next_send_telegram
                   FROM campaign_schedules cs
                   JOIN campaigns c ON cs.campaign_id = c.id
                   WHERE cs.shop_id = ?""",
                (shop_id,),
            )
            rows = cur.fetchall()
            if not rows:
                bot.send_message(chat_id, 'No hay programaciones registradas.')
            else:
                markup = telebot.types.InlineKeyboardMarkup()
                lines = ['📆 *Programaciones:*']
                for r in rows:
                    schedule_id, camp_name, is_active, ids_text, frequency, sched_json, next_send = r
                    status = 'Activa ✅' if is_active else 'Inactiva ❌'
                    freq_text = f' [{frequency}]' if frequency else ''

                    day_map = {
                        'monday': 'lun',
                        'tuesday': 'mar',
                        'wednesday': 'mie',
                        'thursday': 'jue',
                        'friday': 'vie',
                        'saturday': 'sab',
                        'sunday': 'dom',
                    }

                    schedule_parts = []
                    if sched_json:
                        try:
                            data = json.loads(sched_json)
                        except Exception:
                            data = {}
                        day_order = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
                        times_map = {}
                        for d in day_order:
                            hours = data.get(d)
                            if not hours:
                                continue
                            key = tuple(hours)
                            abbr = day_map.get(d, d[:3])
                            times_map.setdefault(key, []).append(abbr)
                        for hours, days_abbr in times_map.items():
                            days_str = ','.join(days_abbr)
                            hours_str = ', '.join(hours)
                            schedule_parts.append(f"{days_str} {hours_str}")
                    schedule_text = ''
                    if schedule_parts:
                        schedule_text = ' - ' + '; '.join(schedule_parts)

                    next_text = ''
                    if next_send:
                        parts = [p.strip() for p in re.split(r'[\n,]+', str(next_send)) if p.strip()]
                        if parts:
                            shown = ', '.join(parts[:2])
                            if len(parts) > 2:
                                shown += ' …'
                            next_text = f" - Próximo: {shown}"

                    group_labels = []
                    if ids_text:
                        try:
                            ids = [int(i) for i in str(ids_text).split(',') if i]
                        except ValueError:
                            ids = []
                        for gid in ids:
                            info = group_map.get(gid)
                            if not info:
                                continue
                            name = info['group_name'] or info['group_id']
                            label = name
                            if info['topic_id'] is not None:
                                label += f" (topic {info['topic_id']})"
                            group_labels.append(label)
                    groups_text = ''
                    if group_labels:
                        groups_text = ' - ' + ', '.join(group_labels)

                    lines.append(
                        f"- {schedule_id} {camp_name}{freq_text} ({status}){schedule_text}{next_text}{groups_text}"
                    )
                    toggle = 'Cancelar' if is_active else 'Reactivar'

                    # Nueva modificación: agregar botones de acción por programación
                    markup.add(
                        telebot.types.InlineKeyboardButton(
                            text=f'{toggle} {schedule_id}',
                            callback_data=f'TOGGLE_SCHEDULE_{schedule_id}'
                        ),
                        telebot.types.InlineKeyboardButton(
                            text=f'🗑️ Eliminar {schedule_id}',
                            callback_data=f'DELETE_SCHEDULE_{schedule_id}'
                        ),
                        telebot.types.InlineKeyboardButton(
                            text=f'✏️ Editar {schedule_id}',
                            callback_data=f'EDIT_SCHEDULE_{schedule_id}'
                        )
                    )
                markup.add(
                    telebot.types.InlineKeyboardButton(
                        text='Cancelar y volver a Marketing',
                        callback_data='Volver a Marketing'
                    )
                )

                MAX_LEN = 3500
                message_chunk = ''
                for line in lines:
                    if len(message_chunk) + len(line) + 1 > MAX_LEN:
                        bot.send_message(chat_id, message_chunk, parse_mode='Markdown')
                        message_chunk = line
                    else:
                        message_chunk += ('\n' if message_chunk else '') + line
                bot.send_message(
                    chat_id,
                    message_chunk,
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
            conn.close()

        elif '🎯 Gestionar grupos' == message_text:
            msg = (
                '🎯 *Gestionar grupos*\n\n'
                'Selecciona una acción o envía /cancel para regresar.'
            )
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row('➕ Agregar grupo', '➖ Eliminar grupo')
            user_markup.row('🧵 Agregar Topic', 'Introducir ID manual')
            user_markup.row('📋 Listar grupos')
            user_markup.row('📢 Marketing')
            bot.send_message(chat_id, msg, reply_markup=user_markup, parse_mode='Markdown')

        elif message_text == '➕ Agregar grupo':
            groups = get_admin_telegram_groups(bot, chat_id)
            if not groups:
                bot.send_message(chat_id, 'No se encontraron grupos disponibles.')
            else:
                markup = telebot.types.ReplyKeyboardMarkup(True, False)
                for g in groups:
                    markup.row(f"{g['title']} ({g['id']})")
                markup.row('Cancelar')
                tmp = f'data/Temp/{chat_id}_group_choices.json'
                os.makedirs('data/Temp', exist_ok=True)
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump(groups, f)
                bot.send_message(chat_id, 'Seleccione el grupo a agregar:', reply_markup=markup)
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 170

        elif message_text == '➖ Eliminar grupo':
            markup = telebot.types.ReplyKeyboardMarkup(True, False)
            markup.row('Cancelar')
            bot.send_message(chat_id, 'Envía el ID del grupo a eliminar:', reply_markup=markup)
            set_state(chat_id, 172, 'marketing')

        elif message_text == '🧵 Agregar Topic':
            markup = telebot.types.ReplyKeyboardMarkup(True, False)
            markup.row('Cancelar')
            bot.send_message(
                chat_id,
                '🧵 *Agregar Topic a un Grupo*\n\n'
                'Formato: `<ID_GRUPO> <ID_TOPIC> [Nombre]`\n\n'
                '*Ejemplo:* `-1001234567890 123 Ventas`\n\n'
                '*¿Cómo obtener el ID del Topic?*\n'
                '1. Ve al topic en Telegram\n'
                '2. Reenvía un mensaje a @userinfobot\n'
                '3. Copia el `message_thread_id`',
                parse_mode='Markdown',
                reply_markup=markup
            )
            set_state(chat_id, 173, 'marketing')

        elif message_text == 'Introducir ID manual':
            markup = telebot.types.ReplyKeyboardMarkup(True, False)
            markup.row('Cancelar')
            bot.send_message(
                chat_id,
                'Envía el ID del grupo y opcionalmente el nombre.\n'
                'Formato: <ID> [Nombre]',
                reply_markup=markup
            )
            set_state(chat_id, 171, 'marketing')

        elif message_text == '📋 Listar grupos':
            conn = db.get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT platform, group_id, group_name, topic_id FROM target_groups WHERE shop_id = ? ORDER BY group_id, topic_id",
                (shop_id,),
            )
            rows = cur.fetchall()
            if rows:
                txt = '🎯 *Grupos y Topics registrados:*\n\n'
                current_group = None
                for r in rows:
                    platform, group_id, group_name, topic_id = r
                    name = group_name or ''
        
                    if topic_id is None:
                        # Grupo principal
                        txt += f"📱 {platform} `{group_id}` {name}\n"
                        current_group = group_id
                    else:
                        # Topic dentro del grupo
                        if current_group != group_id:
                            txt += f"📱 {platform} `{group_id}`\n"
                        txt += f"  └🧵 Topic `{topic_id}` - {name}\n"
                        current_group = group_id
                txt += f"\n*Total: {len(rows)} destinos*"
            else:
                txt = 'No hay grupos registrados.'
            bot.send_message(chat_id, txt, parse_mode='Markdown')

        elif '📊 Estadísticas hoy' == message_text:
            stats = advertising.get_today_stats()
            msg = (
                f"📊 *Estadísticas de hoy*\n\n"
                f"Mensajes enviados: {stats['sent']}\n"
                f"Tasa de éxito: {stats['success_rate']}%\n"
                f"Grupos alcanzados: {stats['groups']}"
            )
            bot.send_message(chat_id, msg, parse_mode='Markdown')

        elif '⚙️ Configuración' == message_text:
            configs = {c['platform']: c for c in advertising.get_platform_configs()}
            tel_status = 'Activo ✅' if configs.get('telegram', {}).get('is_active', True) else 'Inactivo ❌'
            msg_cfg = (
                '⚙️ *Configuración de plataformas*\n\n'
                f'Telegram: {tel_status}'
            )
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row('Toggle telegram')
            user_markup.row('Editar telegram')
            user_markup.row('📢 Marketing')
            bot.send_message(chat_id, msg_cfg, reply_markup=user_markup, parse_mode='Markdown')

        elif message_text == 'Toggle telegram':
            cfg = {c['platform']: c for c in advertising.get_platform_configs()}
            current = cfg.get('telegram', {}).get('is_active', True)
            advertising.update_platform_config('telegram', is_active=not current)
            bot.send_message(chat_id, '✅ Estado de Telegram actualizado')
            in_adminka(chat_id, '⚙️ Configuración', username, name_user)

        elif message_text == 'Editar telegram':
            key = telebot.types.ReplyKeyboardMarkup(True, False)
            key.row('Cancelar')
            bot.send_message(chat_id, 'Envíe la nueva configuración (texto o JSON) para Telegram:', reply_markup=key)
            set_state(chat_id, 175, 'marketing')

        elif message_text.startswith('▶️ Envío manual'):
            params = message_text.replace('▶️ Envío manual', '').strip()
            if not params:
                bot.send_message(chat_id, 'Uso: ▶️ Envío manual <ID>')
            else:
                try:
                    camp_id = int(params.split()[0])
                except ValueError:
                    cancel_and_reset(chat_id)
                    return

                groups = advertising.get_target_groups()
                if not groups:
                    bot.send_message(chat_id, 'No hay grupos activos registrados.')
                    return

                markup = telebot.types.ReplyKeyboardMarkup(True, False)
                for g in groups:
                    title = g['group_name'] or g['group_id']
                    label = f"{title} ({g['group_id']})"
                    if g.get('topic_id') is not None:
                        label += f" (topic {g['topic_id']})"
                    markup.row(label)
                markup.row('Cancelar')
                
                os.makedirs('data/Temp', exist_ok=True)
                tmp = f'data/Temp/{chat_id}_manual_send.json'
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump({'camp_id': camp_id, 'groups': groups}, f)

                bot.send_message(chat_id, 'Seleccione el grupo destino:', reply_markup=markup)
                set_state(chat_id, 176, 'marketing')

        elif 'Vista previa' == message_text:
            preview = f"🛍️ **CATÁLOGO PREVIEW**\n{'-'*30}\n\n{dop.get_productcatalog(shop_id)}"
            bot.send_message(chat_id, preview, parse_mode='Markdown')

        elif normalized in ('a todos los usuarios', 'solo a los compradores', 'solo a compradores'):
            if normalized == 'a todos los usuarios':
                with open('data/Temp/' + str(chat_id) + '.txt', 'w', encoding='utf-8') as f:
                    f.write('all\n')
                amount = dop.user_loger()
            elif normalized in ('solo a los compradores', 'solo a compradores'):
                with open('data/Temp/' + str(chat_id) + '.txt', 'w', encoding='utf-8') as f:
                    f.write('buyers\n')
                amount = dop.get_amountsbayers()
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, '¿A cuántos usuarios desea enviar el boletín? Ingrese un número. Máximo posible ' + str(amount))
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 40

        elif '⚙️ Otros' == message_text:
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            if chat_id == config.admin_id:
                user_markup.row('Añadir nuevo admin', 'Eliminar admin')
            user_markup.row('Cambiar nombre de tienda')
            user_markup.row('Cambiar descripción de tienda')
            user_markup.row('Cambiar multimedia de tienda')
            user_markup.row('Cambiar botones de tienda')
            user_markup.row('Configurar límite de campañas')
            if chat_id == config.admin_id:
                user_markup.row('Cambiar mensaje de inicio (/start)')
            if chat_id == config.admin_id:
                user_markup.row('🛍️ Gestionar tiendas')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, 'Seleccione qué desea hacer', reply_markup=user_markup)

        elif 'Añadir nuevo admin' == message_text:
            if chat_id != config.admin_id:
                bot.send_message(chat_id, '❌ Solo el super admin puede gestionar administradores.')
            else:
                key = telebot.types.InlineKeyboardMarkup()
                key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
                bot.send_message(chat_id, 'Ingrese la ID del nuevo admin')
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 21

        elif 'Eliminar admin' == message_text:
            if chat_id != config.admin_id:
                bot.send_message(chat_id, '❌ Solo el super admin puede gestionar administradores.')
            else:
                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                a = 0
                for admin_id in dop.get_adminlist():
                    a += 1
                    if int(admin_id) != config.admin_id:
                        user_markup.row(str(admin_id))
                if a == 1:
                    bot.send_message(chat_id, '¡Todavía no ha añadido admins!')
                else:
                    user_markup.row('Volver al menú principal')
                    bot.send_message(chat_id, 'Seleccione qué admin desea eliminar', reply_markup=user_markup)
                    with shelve.open(files.sost_bd) as bd:
                        bd[str(chat_id)] = 22

        elif message_text == 'Cambiar nombre de tienda':
            key = telebot.types.ReplyKeyboardMarkup(True, False)
            key.row('Cancelar')
            bot.send_message(chat_id, 'Ingrese el nuevo nombre de la tienda:', reply_markup=key)
            set_state(chat_id, 303, 'other')

        elif message_text == 'Cambiar descripción de tienda':
            key = telebot.types.ReplyKeyboardMarkup(True, False)
            key.row('Cancelar')
            bot.send_message(chat_id, 'Ingrese la nueva descripción (o "ELIMINAR" para borrar):', reply_markup=key)
            set_state(chat_id, 304, 'other')

        elif message_text == 'Cambiar multimedia de tienda':
            key = telebot.types.ReplyKeyboardMarkup(True, False)
            key.row('Cancelar')
            bot.send_message(chat_id, 'Envía una foto o video para la tienda o escribe "ELIMINAR"', reply_markup=key)
            set_state(chat_id, 305, 'other')

        elif message_text == 'Cambiar botones de tienda':
            key = telebot.types.ReplyKeyboardMarkup(True, False)
            key.row('Cancelar')
            bot.send_message(chat_id, 'Texto para el primer botón (o "ninguno"):', reply_markup=key)
            set_state(chat_id, 306, 'other')

        elif message_text == 'Configurar límite de campañas':
            if chat_id == config.admin_id:
                key = telebot.types.ReplyKeyboardMarkup(True, False)
                key.row('Cancelar')
                bot.send_message(chat_id, 'Ingrese el ID de la tienda a configurar:', reply_markup=key)
                set_state(chat_id, 310, 'other')
            else:
                shop_id = dop.get_shop_id(chat_id)
                limit = dop.get_campaign_limit(shop_id)
                key = telebot.types.ReplyKeyboardMarkup(True, False)
                key.row('Cancelar')
                bot.send_message(
                    chat_id,
                    f'Límite actual: {limit}\nIngresa el nuevo límite de campañas:',
                    reply_markup=key
                )
                set_state(chat_id, 311, 'other')

        elif message_text == 'Cambiar mensaje de inicio (/start)' and chat_id == config.admin_id:
            key = telebot.types.ReplyKeyboardMarkup(True, False)
            key.row('Cancelar')
            bot.send_message(chat_id,
                             'Ingrese el nuevo mensaje de inicio. Puede usar `username` y `name`.',
                             parse_mode='Markdown', reply_markup=key)
            set_state(chat_id, 500, 'other')

        elif message_text == '🛍️ Gestionar tiendas' and chat_id == config.admin_id:
            shops = dop.list_shops()
            lines = ['*Tiendas:*']
            for sid, aid, name in shops:
                lines.append(f"{sid}. {name} (admin {aid})")
            bot.send_message(chat_id, '\n'.join(lines), parse_mode='Markdown')
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row('Crear tienda', 'Asignar admin a tienda')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, 'Elige una opción:', reply_markup=user_markup)
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 300


def text_analytics(message_text, chat_id):
    shop_id = dop.get_shop_id(chat_id)
    normalized = message_text.strip().lower()
    if normalized == 'cancelar':
        handle_cancel_command(chat_id)
        return
    if normalized in ('volver al men\u00fa principal', 'volver al menu principal', '/adm'):
        with shelve.open(files.sost_bd) as bd:
            if str(chat_id) in bd:
                del bd[str(chat_id)]
        in_adminka(chat_id, 'Volver al men\u00fa principal', None, None)
        return

    if dop.get_sost(chat_id) is True:
        with shelve.open(files.sost_bd) as bd: 
            sost_num = bd[str(chat_id)]
        
        if sost_num == 1:
            try:
                with open('data/Temp/' + str(chat_id) + '.txt', encoding='utf-8') as f:
                    message = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return
            if message == 'manual_delivery':
                success = dop.save_message('manual_delivery', message_text)
            elif message == 'start':
                media = dop.get_start_media()
                fid = media['file_id'] if media else None
                mtype = media['type'] if media else None
                success = dop.save_message('start', message_text, file_id=fid, media_type=mtype)
            else:
                try:
                    with shelve.open(files.bot_message_bd) as bd:
                        bd[message] = message_text
                    success = True
                except:
                    success = False
            if success:
                user_markup = telebot.types.ReplyKeyboardMarkup(True, True)
                if chat_id == config.admin_id:
                    user_markup.row('💬 Respuestas')
                user_markup.row('📦 Surtido', '➕ Producto')
                user_markup.row('💰 Pagos')
                user_markup.row('📊 Stats', '📣 Difusión')
                user_markup.row('💸 Descuentos')
                user_markup.row('⚙️ Otros')
                bot.send_message(chat_id, 'Mensaje guardado exitosamente!', reply_markup=user_markup)
                with shelve.open(files.sost_bd) as bd: 
                    del bd[str(chat_id)]
            else:
                bot.send_message(chat_id, 'Error guardando mensaje')

        elif sost_num == 2:
            with open('data/Temp/' + str(chat_id) + 'good_name.txt', 'w', encoding='utf-8') as f: 
                f.write(message_text)
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Ahora ingrese la descripción', reply_markup=key)
            with shelve.open(files.sost_bd) as bd: 
                bd[str(chat_id)] = 3

        elif sost_num == 3:
            with open('data/Temp/' + str(chat_id) + 'good_description.txt', 'w', encoding='utf-8') as f:
                f.write(message_text)
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row('Sí', 'No')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, '¿Entrega manual?', reply_markup=user_markup)
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 11

        elif sost_num == 11:
            required_files = [
                f'data/Temp/{chat_id}good_name.txt',
                f'data/Temp/{chat_id}good_description.txt'
            ]
            if not all(os.path.exists(p) for p in required_files):
                cancel_and_reset(chat_id)
                return

            manual_flag = '1' if message_text == 'Sí' else '0'
            with open('data/Temp/' + str(chat_id) + 'good_manual.txt', 'w', encoding='utf-8') as f:
                f.write(manual_flag)
            if manual_flag == '1':
                with open('data/Temp/' + str(chat_id) + 'good_format.txt', 'w', encoding='utf-8') as f2:
                    f2.write('manual')
                key = telebot.types.InlineKeyboardMarkup()
                key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
                bot.send_message(chat_id, 'Ahora ingrese la cantidad disponible en stock', reply_markup=key)
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 12
            else:
                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                user_markup.row('En formato de texto', 'En formato de archivo')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, 'Ahora seleccione el formato del producto', reply_markup=user_markup)
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 4

        elif sost_num == 12:
            try:
                stock_val = int(message_text)
                if stock_val < 0:
                    raise ValueError
            except ValueError:
                cancel_and_reset(chat_id)
                return

            with open('data/Temp/' + str(chat_id) + 'good_manual_stock.txt', 'w', encoding='utf-8') as f:
                f.write(str(stock_val))

            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Ahora ingrese la cantidad mínima para comprar', reply_markup=key)
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 5

        elif sost_num == 4:
            format_map = {
                'En formato de texto': 'text',
                'En formato de archivo': 'file'
            }
            format_value = format_map.get(message_text, message_text)
            with open('data/Temp/' + str(chat_id) + 'good_format.txt', 'w', encoding='utf-8') as f:
                f.write(format_value)
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Ahora ingrese la cantidad mínima para comprar', reply_markup=key)
            with shelve.open(files.sost_bd) as bd: 
                bd[str(chat_id)] = 5

        elif sost_num == 5:
            with open('data/Temp/' + str(chat_id) + 'good_minimum.txt', 'w', encoding='utf-8') as f: 
                f.write(message_text)
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Ahora ingrese el precio por unidad en USD', reply_markup=key)
            with shelve.open(files.sost_bd) as bd: 
                bd[str(chat_id)] = 15

        elif sost_num == 15:
            with open('data/Temp/' + str(chat_id) + 'good_price.txt', 'w', encoding='utf-8') as f:
                f.write(message_text)

            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(
                text='Cancelar y volver al menú principal de administración',
                callback_data='Volver al menú principal de administración'
            ))

            bot.send_message(
                chat_id,
                'Ingrese la duración en días del producto (0 para indefinido):',
                reply_markup=key
            )
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 16

        elif sost_num == 16:
            try:
                duration_val = int(message_text)
                if duration_val < 0:
                    raise ValueError
            except ValueError:
                cancel_and_reset(chat_id)
                return

            with open('data/Temp/' + str(chat_id) + 'good_duration.txt', 'w', encoding='utf-8') as f:
                f.write(str(duration_val))

            cats = dop.list_categories(shop_id)
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            for _cid, cname in cats:
                user_markup.row(cname)
            user_markup.row('Nueva categoría')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, 'Elija una categoría para el producto:', reply_markup=user_markup)
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 62

        elif sost_num == 62:
            if message_text == 'Nueva categoría':
                bot.send_message(chat_id, 'Ingrese el nombre de la nueva categoría:')
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 61
                return

            cat_id = dop.get_category_id(message_text, shop_id)
            if cat_id is None:
                bot.send_message(chat_id, '❌ Categoría no válida. Intente de nuevo.')
                return

            with open('data/Temp/' + str(chat_id) + 'good_category.txt', 'w', encoding='utf-8') as f:
                f.write(str(cat_id))

            try:
                with open('data/Temp/' + str(chat_id) + 'good_name.txt', encoding='utf-8') as f:
                    name = f.read()
                with open('data/Temp/' + str(chat_id) + 'good_description.txt', encoding='utf-8') as f:
                    description = f.read()
                with open('data/Temp/' + str(chat_id) + 'good_format.txt', encoding='utf-8') as f:
                    format_type = f.read()
                format_display = 'Texto' if format_type == 'text' else 'Archivo'
                with open('data/Temp/' + str(chat_id) + 'good_manual.txt', encoding='utf-8') as f:
                    manual_flag = f.read().strip()
                with open('data/Temp/' + str(chat_id) + 'good_minimum.txt', encoding='utf-8') as f:
                    minimum = f.read()
                with open('data/Temp/' + str(chat_id) + 'good_price.txt', encoding='utf-8') as f:
                    price = f.read()
                with open('data/Temp/' + str(chat_id) + 'good_duration.txt', encoding='utf-8') as f:
                    duration_val = int(f.read())
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return

            duration_display = ''
            if duration_val > 0:
                duration_display = f'\n*Duración:* {duration_val} días'

            cat_name = dop.get_category_name(cat_id, shop_id)
            cat_line = f'\n*Categoría:* {cat_name}' if cat_name else ''

            manual_text = 'Sí' if manual_flag == '1' else 'No'
            summary = (
                f'*Resumen del producto:*\n\n*Nombre:* {name}\n*Descripción:* {description}'
                f'\n*Formato:* {format_display}\n*Cantidad mínima:* {minimum}\n*Precio:* ${price} USD{duration_display}{cat_line}'
                f'\n*Entrega manual:* {manual_text}'
            )

            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Añadir producto a la tienda', callback_data='Añadir producto a la tienda'))
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))

            media_temp = 'data/Temp/' + str(chat_id) + 'new_media.txt'
            if os.path.exists(media_temp):
                with open(media_temp, 'r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
                    if len(lines) >= 2:
                        file_id = lines[0]
                        mtype = lines[1]
                        caption = summary
                        if mtype == 'photo':
                            bot.send_photo(chat_id, file_id, caption=caption, reply_markup=key, parse_mode='Markdown')
                        elif mtype == 'video':
                            bot.send_video(chat_id, file_id, caption=caption, reply_markup=key, parse_mode='Markdown')
                        else:
                            bot.send_message(chat_id, summary, parse_mode='MarkDown', reply_markup=key)
                    else:
                        bot.send_message(chat_id, summary, parse_mode='MarkDown', reply_markup=key)
            else:
                bot.send_message(chat_id, summary, parse_mode='MarkDown', reply_markup=key)
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]

        elif sost_num == 61:
            cat_id = dop.create_category(message_text.strip(), shop_id)
            if not cat_id:
                bot.send_message(chat_id, '❌ No se pudo crear la categoría (posiblemente ya existe).')
                return

            with open('data/Temp/' + str(chat_id) + 'good_category.txt', 'w', encoding='utf-8') as f:
                f.write(str(cat_id))

            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 62

            cats = dop.list_categories(shop_id)
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            for _cid, cname in cats:
                user_markup.row(cname)
            user_markup.row('Nueva categoría')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, 'Categoría creada. Seleccione la categoría para continuar:', reply_markup=user_markup)

        elif sost_num == 60:
            cat_id = dop.get_category_id(message_text, shop_id)
            if cat_id is None:
                bot.send_message(chat_id, '❌ Categoría no encontrada.')
            else:
                con = db.get_db_connection()
                cursor = con.cursor()
                cursor.execute('DELETE FROM categories WHERE id = ?', (cat_id,))
                con.commit()
                bot.send_message(chat_id, 'Categoría eliminada.')
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            in_adminka(chat_id, '🏷️ Categorías', None, None)

        elif sost_num == 63:
            temp_path = 'data/Temp/' + str(chat_id) + 'rename_cat.txt'
            if not os.path.exists(temp_path):
                cat_id = dop.get_category_id(message_text, shop_id)
                if cat_id is None:
                    bot.send_message(chat_id, '❌ Categoría no válida. Intente de nuevo.')
                    return
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(str(cat_id))
                bot.send_message(chat_id, 'Ingrese el nuevo nombre para la categoría:')
            else:
                try:
                    with open(temp_path, encoding='utf-8') as f:
                        cat_id = int(f.read())
                except (FileNotFoundError, ValueError):
                    cancel_and_reset(chat_id)
                    return
                success = dop.update_category_name(cat_id, message_text.strip(), shop_id)
                if success:
                    bot.send_message(chat_id, 'Categoría actualizada.')
                else:
                    bot.send_message(chat_id, '❌ Error al actualizar la categoría.')
                os.remove(temp_path)
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                in_adminka(chat_id, '🏷️ Categorías', None, None)

        elif sost_num == 6:
            if message_text not in dop.get_goods(shop_id):
                bot.send_message(chat_id, '¡La posición seleccionada no se encontró! Selecciónela haciendo clic en el botón correspondiente.')
            else:
                dop.delete_product(message_text, shop_id)
                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
                user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
                user_markup.row('Cambiar categoría')
                user_markup.row('📝 Descripción adicional')
                user_markup.row('🎬 Multimedia productos')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '¡Posición eliminada con éxito!', reply_markup=user_markup)
                with shelve.open(files.sost_bd) as bd: 
                    del bd[str(chat_id)]

        elif sost_num == 7:
            if message_text not in dop.get_goods(shop_id):
                bot.send_message(chat_id, '¡No hay una posición con ese nombre!\n¡Seleccione de nuevo!')
            else:
                with open('data/Temp/' + str(chat_id) + '.txt', 'w', encoding='utf-8') as f:
                    f.write(message_text)

                info = (
                    dop.format_product_with_media(message_text, shop_id)
                    if dop.has_product_media(message_text, shop_id)
                    else dop.format_product_basic_info(message_text, shop_id)
                )
                reply = telebot.types.ReplyKeyboardMarkup(True, False)
                reply.row('Volver al menú principal')
                bot.send_message(chat_id, info, parse_mode='Markdown', reply_markup=reply)
                bot.send_message(chat_id, 'Ahora escriba la nueva descripción', parse_mode='Markdown', reply_markup=reply)
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 8

        elif sost_num == 8:
            try:
                with open('data/Temp/' + str(chat_id) + '.txt', encoding='utf-8') as f:
                    name_good = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return

            dop.update_product_description(name_good, message_text, shop_id)
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
            user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
            user_markup.row('Cambiar categoría')
            user_markup.row('📝 Descripción adicional')
            user_markup.row('🎬 Multimedia productos')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, '¡Descripción cambiada con éxito!', reply_markup=user_markup)
            with shelve.open(files.sost_bd) as bd: 
                del bd[str(chat_id)]

        elif sost_num == 9:
            temp_path = 'data/Temp/' + str(chat_id) + '.txt'
            if not os.path.exists(temp_path):
                product = message_text
                if product not in dop.get_goods(shop_id):
                    bot.send_message(chat_id, '❌ Producto no válido')
                    return

                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(product)

                info = (
                    dop.format_product_with_media(product, shop_id)
                    if dop.has_product_media(product, shop_id)
                    else dop.format_product_basic_info(product, shop_id)
                )
                reply = telebot.types.ReplyKeyboardMarkup(True, False)
                reply.row('Volver al menú principal')
                bot.send_message(chat_id, info, parse_mode='Markdown', reply_markup=reply)
                bot.send_message(chat_id, 'Ahora ingrese el nuevo precio', parse_mode='Markdown', reply_markup=reply)
            else:
                try:
                    with open(temp_path, encoding='utf-8') as f:
                        name_good = f.read()
                except FileNotFoundError:
                    cancel_and_reset(chat_id)
                    return
                try:
                    price = int(message_text)
                    dop.update_product_price(name_good, price, shop_id)
                    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                    user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
                    user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
                    user_markup.row('Cambiar categoría')
                    user_markup.row('📝 Descripción adicional')
                    user_markup.row('🎬 Multimedia productos')
                    user_markup.row('Volver al menú principal')
                    bot.send_message(chat_id, '¡Precio cambiado con éxito!', reply_markup=user_markup, parse_mode='Markdown')
                    with shelve.open(files.sost_bd) as bd:
                        del bd[str(chat_id)]
                    os.remove(temp_path)
                except ValueError:
                    cancel_and_reset(chat_id)

        elif sost_num == 64:
            temp_path = f'data/Temp/{chat_id}_edit_cat.txt'
            if not os.path.exists(temp_path):
                product = message_text
                if product not in dop.get_goods(shop_id):
                    bot.send_message(chat_id, '❌ Producto no válido')
                    return

                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(product)

                cats = dop.list_categories(shop_id)
                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                for _cid, cname in cats:
                    user_markup.row(cname)
                user_markup.row('Nueva categoría')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, 'Seleccione la nueva categoría:', reply_markup=user_markup)
            else:
                with open(temp_path, encoding='utf-8') as f:
                    product = f.read()

                if message_text == 'Nueva categoría':
                    bot.send_message(chat_id, 'Ingrese el nombre de la nueva categoría:')
                    with shelve.open(files.sost_bd) as bd:
                        bd[str(chat_id)] = 65
                    return

                cat_id = dop.get_category_id(message_text, shop_id)
                if cat_id is None:
                    bot.send_message(chat_id, '❌ Categoría no válida. Intente de nuevo.')
                    return

                dop.assign_product_category(product, cat_id, shop_id)
                os.remove(temp_path)

                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
                user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
                user_markup.row('Cambiar categoría')
                user_markup.row('📝 Descripción adicional')
                user_markup.row('🎬 Multimedia productos')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, 'Categoría actualizada con éxito.', reply_markup=user_markup)
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]

        elif sost_num == 65:
            temp_path = f'data/Temp/{chat_id}_edit_cat.txt'
            try:
                with open(temp_path, encoding='utf-8') as f:
                    product = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return

            cat_id = dop.create_category(message_text.strip(), shop_id)
            if not cat_id:
                bot.send_message(chat_id, '❌ No se pudo crear la categoría (posiblemente ya existe).')
                return

            dop.assign_product_category(product, cat_id, shop_id)
            os.remove(temp_path)

            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
            user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
            user_markup.row('Cambiar categoría')
            user_markup.row('📝 Descripción adicional')
            user_markup.row('🎬 Multimedia productos')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, 'Categoría creada y asignada con éxito.', reply_markup=user_markup)
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]

        elif sost_num == 10:
            product = message_text
            if product not in dop.get_goods(shop_id):
                bot.send_message(chat_id, '❌ Producto no válido')
                return

            with open('data/Temp/' + str(chat_id) + '_product.txt', 'w', encoding='utf-8') as f:
                f.write(product)

            info = (
                dop.format_product_with_media(product, shop_id)
                if dop.has_product_media(product, shop_id)
                else dop.format_product_basic_info(product, shop_id)
            )
            bot.send_message(chat_id, info, parse_mode='Markdown')

            user_markup = telebot.types.ReplyKeyboardMarkup(True, True)
            user_markup.row('Añadir unidades')
            user_markup.row('Editar unidades', 'Eliminar unidades')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, f'*Producto seleccionado:* {product}\nSeleccione una acción:', reply_markup=user_markup, parse_mode='Markdown')

            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 179

        elif sost_num == 179:
            try:
                with open('data/Temp/' + str(chat_id) + '_product.txt', encoding='utf-8') as f:
                    product = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return

            action = message_text.strip().lower()
            if dop.is_manual_delivery(product, shop_id):
                if action == 'añadir unidades':
                    bot.send_message(chat_id, 'Indique cuántas unidades desea agregar:')
                    with shelve.open(files.sost_bd) as bd:
                        bd[str(chat_id)] = 183
                elif action == 'editar unidades':
                    current = dop.get_manual_stock(product, shop_id)
                    bot.send_message(chat_id, f'Stock actual: {current}\nIndique la nueva cantidad total:')
                    with shelve.open(files.sost_bd) as bd:
                        bd[str(chat_id)] = 184
                elif action == 'eliminar unidades':
                    current = dop.get_manual_stock(product, shop_id)
                    bot.send_message(chat_id, f'Stock actual: {current}\nIndique cuántas unidades desea eliminar:')
                    with shelve.open(files.sost_bd) as bd:
                        bd[str(chat_id)] = 185
                else:
                    show_product_menu(chat_id)
            else:
                file_path = f'data/goods/{shop_id}_{product}.txt'
                if action == 'añadir unidades':
                    bot.send_message(chat_id, 'Envíe las unidades a añadir, una por línea:')
                    with shelve.open(files.sost_bd) as bd:
                        bd[str(chat_id)] = 180
                elif action == 'editar unidades':
                    if not os.path.exists(file_path):
                        bot.send_message(chat_id, 'El producto aún no tiene unidades.')
                        show_product_menu(chat_id)
                        with shelve.open(files.sost_bd) as bd:
                            del bd[str(chat_id)]
                        return
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = [ln.rstrip('\n') for ln in f.readlines()]
                    text = '\n'.join(f'{i+1}. {line}' for i, line in enumerate(lines)) or 'Sin unidades'
                    dop.send_long_text(bot, chat_id, f'Unidades actuales:\n{text}\n\nEnvía "número nuevo_valor" para reemplazar la línea:')
                    with shelve.open(files.sost_bd) as bd:
                        bd[str(chat_id)] = 181
                elif action == 'eliminar unidades':
                    if not os.path.exists(file_path):
                        bot.send_message(chat_id, 'El producto aún no tiene unidades.')
                        show_product_menu(chat_id)
                        with shelve.open(files.sost_bd) as bd:
                            del bd[str(chat_id)]
                        return
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = [ln.rstrip('\n') for ln in f.readlines()]
                    text = '\n'.join(f'{i+1}. {line}' for i, line in enumerate(lines)) or 'Sin unidades'
                    dop.send_long_text(bot, chat_id, f'Unidades actuales:\n{text}\n\nIndique los números de línea a eliminar separados por espacios:')
                    with shelve.open(files.sost_bd) as bd:
                        bd[str(chat_id)] = 182
                else:
                    show_product_menu(chat_id)

        elif sost_num == 180:
            try:
                with open('data/Temp/' + str(chat_id) + '_product.txt', encoding='utf-8') as f:
                    product = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return
            file_path = f'data/goods/{shop_id}_{product}.txt'
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(message_text + '\n')
            bot.send_message(chat_id, '¡Unidades añadidas con éxito!')
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            show_product_menu(chat_id)

        elif sost_num == 181:
            try:
                with open('data/Temp/' + str(chat_id) + '_product.txt', encoding='utf-8') as f:
                    product = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return
            file_path = f'data/goods/{shop_id}_{product}.txt'
            if not os.path.exists(file_path):
                bot.send_message(chat_id, '❌ Archivo de producto no encontrado')
                show_product_menu(chat_id)
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                return
            parts = message_text.split(' ', 1)
            if len(parts) != 2 or not parts[0].isdigit():
                bot.send_message(chat_id, 'Formato incorrecto. Use "número nuevo_texto"')
                return
            idx = int(parts[0]) - 1
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [ln.rstrip('\n') for ln in f.readlines()]
            if idx < 0 or idx >= len(lines):
                bot.send_message(chat_id, 'Número fuera de rango')
                return
            lines[idx] = parts[1]
            with open(file_path, 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(line + '\n')
            bot.send_message(chat_id, '¡Unidades editadas con éxito!')
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            show_product_menu(chat_id)

        elif sost_num == 182:
            try:
                with open('data/Temp/' + str(chat_id) + '_product.txt', encoding='utf-8') as f:
                    product = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return
            file_path = f'data/goods/{shop_id}_{product}.txt'
            if not os.path.exists(file_path):
                bot.send_message(chat_id, '❌ Archivo de producto no encontrado')
                show_product_menu(chat_id)
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                return
            try:
                indices = [int(i)-1 for i in message_text.replace(',', ' ').split()]
            except ValueError:
                cancel_and_reset(chat_id)
                return
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [ln.rstrip('\n') for ln in f.readlines()]
            new_lines = [line for i, line in enumerate(lines) if i not in indices]
            with open(file_path, 'w', encoding='utf-8') as f:
                for line in new_lines:
                    f.write(line + '\n')
            bot.send_message(chat_id, '¡Unidades eliminadas con éxito!')
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            show_product_menu(chat_id)

        elif sost_num == 183:
            try:
                with open('data/Temp/' + str(chat_id) + '_product.txt', encoding='utf-8') as f:
                    product = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return
            try:
                qty = int(message_text)
                if qty < 0:
                    raise ValueError
            except ValueError:
                cancel_and_reset(chat_id)
                return
            dop.add_manual_stock(product, qty, shop_id)
            bot.send_message(chat_id, '¡Unidades añadidas con éxito!')
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            show_product_menu(chat_id)

        elif sost_num == 184:
            try:
                with open('data/Temp/' + str(chat_id) + '_product.txt', encoding='utf-8') as f:
                    product = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return
            try:
                qty = int(message_text)
                if qty < 0:
                    raise ValueError
            except ValueError:
                cancel_and_reset(chat_id)
                return
            dop.set_manual_stock(product, qty, shop_id)
            bot.send_message(chat_id, '¡Unidades editadas con éxito!')
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            show_product_menu(chat_id)

        elif sost_num == 185:
            try:
                with open('data/Temp/' + str(chat_id) + '_product.txt', encoding='utf-8') as f:
                    product = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return
            try:
                qty = int(message_text)
                if qty < 0:
                    raise ValueError
            except ValueError:
                cancel_and_reset(chat_id)
                return
            dop.decrement_manual_stock(product, qty, shop_id)
            bot.send_message(chat_id, '¡Unidades eliminadas con éxito!')
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            show_product_menu(chat_id)

        elif sost_num == 186:
            path = f'data/Temp/{chat_id}_edit_schedule.txt'
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    schedule_id = int(f.read())
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return
            parts = message_text.split()
            if len(parts) < 2:
                bot.send_message(chat_id, 'Formato inválido. Usa "lunes,martes 10:00 12:00"')
                return
            days = parts[0].split(',')
            times = parts[1:]

            groups = advertising.get_target_groups()
            if not groups:
                scheduler = CampaignScheduler(files.main_db, shop_id)
                ok = scheduler.update_schedule(schedule_id, days, times)
                bot.send_message(chat_id, '✅ Programación actualizada' if ok else '❌ Error actualizando programación')
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                try:
                    os.remove(path)
                except Exception:
                    pass
                show_marketing_menu(chat_id)
            else:
                markup = telebot.types.ReplyKeyboardMarkup(True, False)
                for g in groups:
                    title = g['group_name'] or g['group_id']
                    label = f"{title} ({g['id']})"
                    if g.get('topic_id') is not None:
                        label += f" (topic {g['topic_id']})"
                    markup.row(label)
                markup.row('Todos', 'Cancelar')

                os.makedirs('data/Temp', exist_ok=True)
                tmp = f'data/Temp/{chat_id}_schedule.json'
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump({'type': 'edit', 'schedule_id': schedule_id, 'days': days, 'times': times, 'groups': groups}, f)

                bot.send_message(chat_id, 'Seleccione los grupos destino (enviar IDs separados por coma o "Todos"):', reply_markup=markup)
                set_state(chat_id, 187, 'marketing')

        elif sost_num == 18:
            # PayPal Client ID
            with open('data/Temp/' + str(chat_id) + 'paypal_client.txt', 'w', encoding='utf-8') as f:
                f.write(message_text)
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Ahora ingrese el Client Secret de PayPal:', reply_markup=key)
            with shelve.open(files.sost_bd) as bd: 
                bd[str(chat_id)] = 25

        elif sost_num == 25:
            # PayPal Client Secret
            try:
                with open('data/Temp/' + str(chat_id) + 'paypal_client.txt', encoding='utf-8') as f:
                    client_id = f.read()

                shop_id = dop.get_shop_id(chat_id)
                dop.save_paypaldata(client_id, message_text, 1, shop_id)

                with shelve.open(files.payments_bd) as bd:
                    bd['paypal'] = '✅'

                bot.send_message(chat_id, '¡Credenciales PayPal guardadas exitosamente!')
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
            except FileNotFoundError:
                cancel_and_reset(chat_id)
            except Exception as e:
                bot.send_message(chat_id, f'Error guardando credenciales: {e}')

        elif sost_num == 19:
            # Binance API Key
            with open('data/Temp/' + str(chat_id) + 'binance_api.txt', 'w', encoding='utf-8') as f: 
                f.write(message_text)
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Ahora ingrese el API Secret de Binance:', reply_markup=key)
            with shelve.open(files.sost_bd) as bd: 
                bd[str(chat_id)] = 26

        elif sost_num == 26:
            # Binance API Secret
            try:
                with open('data/Temp/' + str(chat_id) + 'binance_api.txt', encoding='utf-8') as f:
                    api_key = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Finalmente, ingrese el Merchant ID de Binance:', reply_markup=key)
            with open('data/Temp/' + str(chat_id) + 'binance_secret.txt', 'w', encoding='utf-8') as f: 
                f.write(message_text)
            with open('data/Temp/' + str(chat_id) + 'binance_api_temp.txt', 'w', encoding='utf-8') as f: 
                f.write(api_key)
            with shelve.open(files.sost_bd) as bd: 
                bd[str(chat_id)] = 27

        elif sost_num == 27:
            # Binance Merchant ID
            try:
                with open('data/Temp/' + str(chat_id) + 'binance_api_temp.txt', encoding='utf-8') as f:
                    api_key = f.read()
                with open('data/Temp/' + str(chat_id) + 'binance_secret.txt', encoding='utf-8') as f:
                    api_secret = f.read()
            
                shop_id = dop.get_shop_id(chat_id)
                dop.save_binancedata(api_key, api_secret, message_text, shop_id)

                with shelve.open(files.payments_bd) as bd:
                    bd['binance'] = '✅'

                bot.send_message(chat_id, '¡Credenciales Binance guardadas exitosamente!')
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
            except FileNotFoundError:
                cancel_and_reset(chat_id)
            except Exception as e:
                bot.send_message(chat_id, f'Error guardando credenciales: {e}')

        elif sost_num == 300 and chat_id == config.admin_id:
            if message_text == 'Crear tienda':
                bot.send_message(chat_id, 'Ingrese el nombre de la tienda:')
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 301
            elif message_text == 'Asignar admin a tienda':
                bot.send_message(chat_id, 'Envía "<shop_id> <admin_id>"')
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 302
            else:
                in_adminka(chat_id, '⚙️ Otros', None, None)

        elif sost_num == 301 and chat_id == config.admin_id:
            shop_id_created = dop.create_shop(message_text.strip())
            if shop_id_created:
                bot.send_message(chat_id, f'Tienda creada con ID {shop_id_created}')
            else:
                bot.send_message(chat_id, '❌ Error creando tienda')
            in_adminka(chat_id, '🛍️ Gestionar tiendas', None, None)
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]

        elif sost_num == 302 and chat_id == config.admin_id:
            parts = message_text.split()
            if len(parts) != 2:
                bot.send_message(chat_id, 'Formato inválido. Usa "<shop_id> <admin_id>"')
                return
            try:
                sid = int(parts[0])
                aid = int(parts[1])
            except ValueError:
                cancel_and_reset(chat_id)
                return
            if dop.assign_admin_to_shop(sid, aid):
                dop.new_admin(aid)
                bot.send_message(chat_id, '✅ Admin asignado correctamente')
            else:
                bot.send_message(chat_id, '❌ Error asignando admin')
            in_adminka(chat_id, '🛍️ Gestionar tiendas', None, None)
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]

        elif sost_num == 303:
            shop_id = dop.get_shop_id(chat_id)
            if dop.update_shop_name(shop_id, message_text.strip()):
                bot.send_message(chat_id, 'Nombre de tienda actualizado.')
            else:
                bot.send_message(chat_id, '❌ Error actualizando nombre de tienda')
            in_adminka(chat_id, '⚙️ Otros', None, None)
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]

        elif sost_num == 304:
            shop_id = dop.get_shop_id(chat_id)
            desc = '' if message_text.upper() == 'ELIMINAR' else message_text
            dop.update_shop_info(shop_id, description=desc)
            bot.send_message(chat_id, 'Descripción actualizada.')
            in_adminka(chat_id, '⚙️ Otros', None, None)
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]

        elif sost_num == 305:
            if message_text.upper() == 'ELIMINAR':
                shop_id = dop.get_shop_id(chat_id)
                dop.update_shop_info(shop_id, media_file_id=None, media_type=None)
                bot.send_message(chat_id, 'Multimedia eliminada.')
                in_adminka(chat_id, '⚙️ Otros', None, None)
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
            else:
                bot.send_message(chat_id, 'Envía una foto o video o escribe ELIMINAR.')

        elif sost_num == 306:
            with open(f'data/Temp/{chat_id}_shop_buttons.txt', 'w', encoding='utf-8') as f:
                f.write(('' if message_text.lower() == 'ninguno' else message_text) + '\n')
            bot.send_message(chat_id, 'URL del primer botón (o "ninguno"):')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 307

        elif sost_num == 307:
            path = f'data/Temp/{chat_id}_shop_buttons.txt'
            with open(path, 'a', encoding='utf-8') as f:
                f.write(('' if message_text.lower() == 'ninguno' else message_text) + '\n')
            bot.send_message(chat_id, 'Texto del segundo botón (o "ninguno"):')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 308

        elif sost_num == 308:
            path = f'data/Temp/{chat_id}_shop_buttons.txt'
            with open(path, 'a', encoding='utf-8') as f:
                f.write(('' if message_text.lower() == 'ninguno' else message_text) + '\n')
            bot.send_message(chat_id, 'URL del segundo botón (o "ninguno"):')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 309

        elif sost_num == 309:
            path = f'data/Temp/{chat_id}_shop_buttons.txt'
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    b1_text = f.readline().rstrip('\n')
                    b1_url = f.readline().rstrip('\n')
                    b2_text = f.readline().rstrip('\n')
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return
            b2_url = '' if message_text.lower() == 'ninguno' else message_text
            shop_id = dop.get_shop_id(chat_id)
            dop.update_shop_info(shop_id,
                                button1_text=b1_text, button1_url=b1_url,
                                button2_text=b2_text, button2_url=b2_url)
            bot.send_message(chat_id, 'Botones actualizados.')
            in_adminka(chat_id, '⚙️ Otros', None, None)
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            os.remove(path)

        elif sost_num == 310 and chat_id == config.admin_id:
            try:
                shop_id_target = int(message_text)
            except ValueError:
                cancel_and_reset(chat_id)
                return
            limit = dop.get_campaign_limit(shop_id_target)
            with open(f'data/Temp/{chat_id}_camp_limit_shop.txt', 'w', encoding='utf-8') as f:
                f.write(str(shop_id_target))
            bot.send_message(chat_id, f'Límite actual: {limit}\nIngresa el nuevo límite de campañas:')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 311

        elif sost_num == 311:
            try:
                new_limit = int(message_text)
                if new_limit < 0:
                    raise ValueError
            except ValueError:
                cancel_and_reset(chat_id)
                return
            if chat_id == config.admin_id:
                try:
                    with open(f'data/Temp/{chat_id}_camp_limit_shop.txt', 'r', encoding='utf-8') as f:
                        shop_id_target = int(f.read().strip())
                except Exception:
                    shop_id_target = dop.get_shop_id(chat_id)
            else:
                shop_id_target = dop.get_shop_id(chat_id)
            if dop.set_campaign_limit(shop_id_target, new_limit):
                bot.send_message(chat_id, '✅ Límite actualizado.')
            else:
                bot.send_message(chat_id, '❌ Error actualizando límite.')
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            if chat_id == config.admin_id:
                try:
                    os.remove(f'data/Temp/{chat_id}_camp_limit_shop.txt')
                except Exception:
                    pass
            in_adminka(chat_id, '⚙️ Otros', None, None)

        elif sost_num == 500:
            text_path = f'data/Temp/{chat_id}_start_text.txt'
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(message_text)
            key = telebot.types.InlineKeyboardMarkup()
            key.add(
                telebot.types.InlineKeyboardButton(
                    text='Omitir', callback_data='SKIP_START_MEDIA'
                )
            )
            key.add(
                telebot.types.InlineKeyboardButton(
                    text='Cancelar y volver al menú principal de administración',
                    callback_data='Volver al menú principal de administración'
                )
            )
            bot.send_message(
                chat_id,
                'Envía una foto, video, documento, audio o GIF para el mensaje de inicio (opcional) o presiona "Omitir"',
                reply_markup=key
            )
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 501

        elif sost_num == 21:
            if chat_id != config.admin_id:
                bot.send_message(chat_id, '❌ No tiene permiso para agregar administradores.')
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
            else:
                dop.new_admin(message_text)
                user_markup = telebot.types.ReplyKeyboardMarkup(True, True)
                user_markup.row('Añadir nuevo admin', 'Eliminar admin')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, 'Nuevo admin añadido con éxito', reply_markup=user_markup)
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]

        elif sost_num == 22:
            if chat_id != config.admin_id:
                bot.send_message(chat_id, '❌ No tiene permiso para eliminar administradores.')
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
            else:
                with open(files.admins_list, encoding='utf-8') as f:
                    if str(message_text) in f.read():
                        dop.del_id(files.admins_list, message_text)
                        bot.send_message(chat_id, 'Admin eliminado con éxito de la lista')
                        with shelve.open(files.sost_bd) as bd:
                            del bd[str(chat_id)]
                    else:
                        bot.send_message(chat_id, '¡La ID no se encontró en la lista de administradores! Seleccione la ID correcta.')
                        with shelve.open(files.sost_bd) as bd :
                            bd[str(chat_id)] = 22

        elif sost_num == 28:  # Seleccionar producto para editar descripción adicional
            if message_text not in dop.get_goods(shop_id):
                bot.send_message(chat_id, '¡La posición seleccionada no se encontró! Selecciónela haciendo clic en el botón correspondiente.')
            else:
                # Mostrar descripción adicional actual
                current_additional = dop.get_additional_description(message_text, shop_id)
                if not current_additional:
                    current_additional = "Sin descripción adicional"

                with open('data/Temp/' + str(chat_id) + 'edit_additional_desc.txt', 'w', encoding='utf-8') as f:
                    f.write(message_text)

                key = telebot.types.InlineKeyboardMarkup()
                key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))

                bot.send_message(chat_id,
                                 f'📝 **Editar descripción adicional para:** {message_text}\n\n'
                                 f'**Descripción adicional actual:**\n{current_additional}\n\n'
                                 f'**Ingrese la nueva descripción adicional** (o escriba "ELIMINAR" para quitar la descripción adicional):',
                                 reply_markup=key, parse_mode='Markdown')

                with shelve.open(files.sost_bd) as bd: 
                    bd[str(chat_id)] = 29

        elif sost_num == 29:  # Recibir nueva descripción adicional
            try:
                with open('data/Temp/' + str(chat_id) + 'edit_additional_desc.txt', encoding='utf-8') as f:
                    product_name = f.read()
            
                if message_text.upper() == "ELIMINAR":
                    new_additional_desc = ""
                    success_message = "La descripción adicional ha sido eliminada."
                else:
                    new_additional_desc = message_text
                    success_message = "La descripción adicional ha sido actualizada."

                if dop.set_additional_description(product_name, new_additional_desc, shop_id):
                    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                    user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
                    user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
                    user_markup.row('Cambiar categoría')
                    user_markup.row('📝 Descripción adicional')
                    user_markup.row('🎬 Multimedia productos')
                    user_markup.row('Volver al menú principal')

                    bot.send_message(chat_id, f'✅ {success_message}\n\nProducto: {product_name}', reply_markup=user_markup)
                    with shelve.open(files.sost_bd) as bd: 
                        del bd[str(chat_id)]
                else:
                    bot.send_message(chat_id, '❌ Error al actualizar la descripción adicional. Inténtelo de nuevo.')
            except FileNotFoundError:
                cancel_and_reset(chat_id)
            except Exception as e:
                logging.error(f"Error en estado 29: {e}")
                bot.send_message(chat_id, '❌ Error procesando la descripción adicional. Inténtelo de nuevo.')

        elif sost_num == 30:  # Seleccionar producto para agregar multimedia
            clean_name = message_text
            for emoji in ['📸 ', '🎥 ', '📄 ', '🎵 ', '📎 ']:
                clean_name = clean_name.replace(emoji, '')

            if clean_name in dop.get_goods(shop_id):
                with open('data/Temp/' + str(chat_id) + 'media_product.txt', 'w', encoding='utf-8') as f:
                    f.write(clean_name)
                
                key = telebot.types.InlineKeyboardMarkup()
                key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='Volver al menú principal de administración'))
                
                bot.send_message(chat_id,
                                f'📤 **Agregar o cambiar multimedia a:** {clean_name}\n\n'
                                f'Envía el archivo multimedia (foto, video, documento, audio, GIF)\n'
                                f'💡 Tip: Puedes añadir un texto descriptivo junto al archivo',
                                reply_markup=key, parse_mode='Markdown')
                
                with shelve.open(files.sost_bd) as bd: 
                    bd[str(chat_id)] = 32
            else:
                bot.send_message(chat_id, '❌ Producto no válido')

        elif sost_num == 31:  # Seleccionar producto para eliminar multimedia
            clean_name = message_text
            for emoji in ['📸 ', '🎥 ', '📄 ', '🎵 ', '📎 ']:
                clean_name = clean_name.replace(emoji, '')
            
            if dop.has_product_media(clean_name, shop_id):
                if dop.remove_product_media(clean_name, shop_id):
                    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                    user_markup.row('🎬 Multimedia productos')
                    user_markup.row('Volver al menú principal')
                    bot.send_message(chat_id, f'✅ Multimedia eliminada del producto: {clean_name}', reply_markup=user_markup)
                else:
                    bot.send_message(chat_id, '❌ Error eliminando multimedia')
            else:
                bot.send_message(chat_id, '❌ El producto no tiene multimedia asignada')
            
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]

        elif sost_num == 33:  # Recibir nuevo texto de descuento
            shop_id = dop.get_shop_id(chat_id)
            if dop.update_discount_config(text=message_text, shop_id=shop_id):
                bot.send_message(chat_id, '✅ Texto de descuento actualizado')
            else:
                bot.send_message(chat_id, '❌ Error actualizando texto')

            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            show_discount_menu(chat_id)

        elif sost_num == 40:  # Cantidad de destinatarios
            try:
                amount = int(message_text)
                if amount <= 0:
                    raise ValueError
            except ValueError:
                cancel_and_reset(chat_id)
                return

            with open('data/Temp/' + str(chat_id) + '.txt', 'a', encoding='utf-8') as f:
                f.write(str(amount) + '\n')

            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Ingrese el texto del anuncio', reply_markup=key)
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 41

        elif sost_num == 41:  # Texto del anuncio
            with open('data/Temp/' + str(chat_id) + '.txt', 'a', encoding='utf-8') as f:
                f.write(message_text + '\n')

            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, 'Si desea añadir un archivo multimedia envíelo ahora o escriba "no"', reply_markup=key)
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 42

        elif sost_num == 42:  # Archivo multimedia opcional
            try:
                with open('data/Temp/' + str(chat_id) + '.txt', encoding='utf-8') as f:
                    lines = f.read().splitlines()
                group = lines[0]
                amount = int(lines[1])
                text = lines[2]
            except Exception:
                cancel_and_reset(chat_id)
                return

            if message_text.lower().strip() in ('no', 'skip', 'sin archivo'):
                shop_id = dop.get_shop_id(chat_id)
                result = dop.broadcast_message(group, amount, text, shop_id=shop_id)
                bot.send_message(chat_id, result)
                try:
                    os.remove('data/Temp/' + str(chat_id) + '.txt')
                except Exception:
                    pass
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
            else:
                bot.send_message(chat_id, 'Envía un archivo multimedia o escribe "no" para continuar sin archivo.')

        elif sost_num == 34:  # Recibir nuevo porcentaje de descuento
            try:
                percent = int(message_text)
                shop_id = dop.get_shop_id(chat_id)
                if dop.update_active_discount_percent(percent, shop_id=shop_id):
                    bot.send_message(chat_id, f'✅ Porcentaje actualizado a {percent}%')
                else:
                    bot.send_message(chat_id, '❌ Error actualizando porcentaje')
            except ValueError:
                cancel_and_reset(chat_id)

            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            show_discount_menu(chat_id)

        elif sost_num == 71:
            try:
                percent = int(message_text)
            except ValueError:
                cancel_and_reset(chat_id)
                return
            with open(f'data/Temp/{chat_id}_discount.txt', 'w', encoding='utf-8') as f:
                f.write(str(percent))
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='GLOBAL_CANCEL'))
            bot.send_message(chat_id, 'Duración en horas (0 permanente):', reply_markup=key)
            set_state(chat_id, 72, 'discount')

        elif sost_num == 72:
            try:
                hours = int(message_text)
            except ValueError:
                cancel_and_reset(chat_id)
                return
            with open(f'data/Temp/{chat_id}_discount.txt', 'a', encoding='utf-8') as f:
                f.write('\n' + str(hours))
            cats = dop.list_categories(shop_id)
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            for _cid, cname in cats:
                user_markup.row(cname)
            user_markup.row('Sin categoría')
            user_markup.row('Cancelar')
            bot.send_message(chat_id, 'Seleccione categoría (o "Sin categoría"):', reply_markup=user_markup)
            set_state(chat_id, 73, 'discount')

        elif sost_num == 73:
            try:
                with open(f'data/Temp/{chat_id}_discount.txt', encoding='utf-8') as f:
                    lines = f.read().splitlines()
                percent = int(lines[0])
                hours = int(lines[1])
            except Exception:
                cancel_and_reset(chat_id)
                return
            os.remove(f'data/Temp/{chat_id}_discount.txt')
            category_id = None
            if message_text != 'Sin categoría':
                category_id = dop.get_category_id(message_text, shop_id)
            start = datetime.datetime.utcnow()
            end = start + datetime.timedelta(hours=hours) if hours > 0 else None
            did = dop.create_discount(percent, start, end, category_id, shop_id)
            bot.send_message(chat_id, '✅ Descuento creado' if did else '❌ Error creando descuento')
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            show_discount_menu(chat_id)

        elif sost_num == 160:  # Nombre de campaña
            with open('data/Temp/' + str(chat_id) + 'campaign_name.txt', 'w', encoding='utf-8') as f:
                f.write(message_text)
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver a Marketing', callback_data='Volver a Marketing'))
            bot.send_message(chat_id, '📝 **Mensaje de la campaña**\n\nEscribe el texto que se enviará (máximo 500 caracteres):', reply_markup=key, parse_mode='Markdown')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 161

        elif sost_num == 161:  # Mensaje de campaña
            if len(message_text) > 500:
                bot.send_message(chat_id, '❌ El mensaje es muy largo. Máximo 500 caracteres.')
                return

            with open('data/Temp/' + str(chat_id) + 'campaign_message.txt', 'w', encoding='utf-8') as f:
                f.write(message_text)

            bot.send_message(chat_id, 'Si deseas adjuntar una foto, video o documento envíalo ahora o escribe "no" para omitir:')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 162

        elif sost_num == 162:  # Multimedia opcional
            if message_text.lower() in ('no', 'sin archivo'):
                bot.send_message(chat_id, 'Si deseas agregar un botón escribe:\n<texto> <url>\nEscribe "no" para continuar sin botones:')
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 163
            else:
                bot.send_message(chat_id, '❌ Envía la foto, video o documento o escribe "no" para continuar sin archivo.')

        elif sost_num == 163:  # Crear campaña
            button1_text = None
            button1_url = None
            if message_text.lower() not in ('no', 'sin botones'):
                parts = message_text.split()
                if len(parts) >= 2:
                    button1_text = parts[0]
                    button1_url = parts[1]

            try:
                with open('data/Temp/' + str(chat_id) + 'campaign_name.txt', encoding='utf-8') as f:
                    name = f.read()
                with open('data/Temp/' + str(chat_id) + 'campaign_message.txt', encoding='utf-8') as f:
                    text = f.read()
                media_file_id = None
                media_type = None
                media_path = f'data/Temp/{chat_id}_campaign_media.txt'
                if os.path.exists(media_path):
                    with open(media_path, 'r', encoding='utf-8') as mf:
                        lines = mf.read().splitlines()
                        if len(lines) >= 2:
                            media_file_id = lines[0]
                            media_type = lines[1]
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return

            data = {
                'name': name,
                'message_text': text,
                'media_file_id': media_file_id,
                'media_type': media_type,
                'button1_text': button1_text,
                'button1_url': button1_url,
                'created_by': chat_id,
            }
            ok, msg = create_campaign_from_admin(data)
            if ok:
                bot.send_message(chat_id, '✅ ' + msg)
            else:
                bot.send_message(chat_id, '❌ ' + msg)
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            try:
                if os.path.exists(media_path):
                    os.remove(media_path)
            except Exception:
                pass

        elif sost_num == 190:  # Selección de producto
            if message_text == 'Cancelar':
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                show_marketing_menu(chat_id)
            else:
                goods = dop.get_goods(shop_id)
                if message_text not in goods:
                    bot.send_message(chat_id, 'Selección inválida. Intente nuevamente.')
                    return
                finalize_product_campaign(chat_id, shop_id, message_text)

        elif sost_num == 165:  # Guardar texto o multimedia editada
            path = f'data/Temp/{chat_id}_edit_campaign.txt'
            data_path = f'data/Temp/{chat_id}_edit_campaign_data.json'
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    _ = int(f.read())
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return

            os.makedirs('data/Temp', exist_ok=True)
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump({'message_text': message_text}, f)

            bot.send_message(chat_id,
                             'Si deseas agregar un botón escribe:\n<texto> <url>'
                             '\nEscribe "no" para continuar sin botones:')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 166

        elif sost_num == 166:  # Primer botón para campaña editada
            data_path = f'data/Temp/{chat_id}_edit_campaign_data.json'
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return

            if message_text.lower() not in ('no', 'sin botones'):
                parts = message_text.split()
                if len(parts) >= 2:
                    data['button1_text'] = parts[0]
                    data['button1_url'] = parts[1]

            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)

            bot.send_message(chat_id,
                             'Si deseas agregar un segundo botón escribe:\n<texto> <url>'
                             '\nEscribe "no" para continuar sin segundo botón:')
            with shelve.open(files.sost_bd) as bd:
                bd[str(chat_id)] = 167

        elif sost_num == 167:  # Segundo botón y aplicar cambios
            path = f'data/Temp/{chat_id}_edit_campaign.txt'
            data_path = f'data/Temp/{chat_id}_edit_campaign_data.json'
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    cid = int(f.read())
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return

            if message_text.lower() not in ('no', 'sin botones'):
                parts = message_text.split()
                if len(parts) >= 2:
                    data['button2_text'] = parts[0]
                    data['button2_url'] = parts[1]

            updates = {k: v for k, v in data.items() if k in (
                'message_text', 'media_file_id', 'media_type',
                'button1_text', 'button1_url', 'button2_text', 'button2_url'
            )}
            ok = advertising.update_campaign(cid, updates)
            bot.send_message(chat_id, ('✅ ' if ok else '❌ ') + 'Campaña actualizada')
            with shelve.open(files.sost_bd) as bd:
                if str(chat_id) in bd:
                    del bd[str(chat_id)]
            try:
                os.remove(path)
                os.remove(data_path)
            except Exception:
                pass

        elif sost_num == 168:  # Eliminar campaña
            cid_text = message_text.strip()
            if not cid_text.isdigit():
                bot.send_message(chat_id, '❌ ID de campaña inválido')
            else:
                cid = int(cid_text)
                ok = advertising.delete_campaign(cid)
                msg = 'Campaña eliminada' if ok else 'Campaña no encontrada'
                bot.send_message(chat_id, ('✅ ' if ok else '❌ ') + msg)
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            show_marketing_menu(chat_id)

        elif sost_num == 170:  # Selección de grupo de Telegram
            tmp = f'data/Temp/{chat_id}_group_choices.json'
            if message_text == 'Cancelar':
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                if os.path.exists(tmp):
                    os.remove(tmp)
                bot.send_message(chat_id, 'Operación cancelada.')
            else:
                try:
                    with open(tmp, 'r', encoding='utf-8') as f:
                        groups = json.load(f)
                except FileNotFoundError:
                    cancel_and_reset(chat_id)
                    return
                selected = next((g for g in groups if f"{g['title']} ({g['id']})" == message_text), None)
                if not selected:
                    bot.send_message(chat_id, 'Selección inválida. Intente nuevamente.')
                    return
                ok, msg = add_target_group_from_admin('telegram', selected['id'], selected['title'])
                bot.send_message(chat_id, ('✅ ' if ok else '❌ ') + msg)
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                if os.path.exists(tmp):
                    os.remove(tmp)

        elif sost_num == 171:  # Agregar grupo introduciendo ID manual
            text = message_text.strip()
            parts = text.split(maxsplit=1)
            if not parts or not parts[0].lstrip('-').isdigit():
                bot.send_message(chat_id, '❌ ID de grupo inválido')
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
            else:
                gid = parts[0]
                name = parts[1] if len(parts) > 1 else None
                ok, msg = add_target_group_from_admin('telegram', gid, name)
                bot.send_message(chat_id, ('✅ ' if ok else '❌ ') + msg)
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]

        elif sost_num == 172:  # Eliminar grupo
            gid = message_text.strip()
            ok, msg = advertising.remove_target_group(gid)
            bot.send_message(chat_id, ('✅ ' if ok else '❌ ') + msg)
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]

        elif sost_num == 173:  # Agregar topic a grupo existente
            text = message_text.strip()
            parts = text.split(maxsplit=2)
            if len(parts) < 2 or not parts[0].lstrip('-').isdigit() or not parts[1].isdigit():
                bot.send_message(chat_id, '❌ Formato inválido. Use: <ID_GRUPO> <ID_TOPIC> [Nombre]')
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
            else:
                group_id = parts[0]
                topic_id = int(parts[1])
                topic_name = parts[2] if len(parts) > 2 else f"Topic {topic_id}"
                
                conn = db.get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO target_groups 
                       (platform, group_id, group_name, topic_id, status, added_date, shop_id)
                       VALUES (?, ?, ?, ?, 'active', ?, ?)""",
                    ('telegram', group_id, topic_name, topic_id, 
                     datetime.datetime.now().isoformat(), shop_id)
                )
                conn.commit()
                bot.send_message(chat_id, f'✅ Topic {topic_id} agregado al grupo {group_id}')
                
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]

        elif sost_num == 175:  # Editar config telegram
            advertising.update_platform_config('telegram', config_data=message_text)
            bot.send_message(chat_id, '✅ Configuración de Telegram actualizada')
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]

        elif sost_num == 176:  # Envío manual a grupo
            tmp = f'data/Temp/{chat_id}_manual_send.json'
            if message_text == 'Cancelar':
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                if os.path.exists(tmp):
                    os.remove(tmp)
                show_marketing_menu(chat_id)
            else:
                try:
                    with open(tmp, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except FileNotFoundError:
                    cancel_and_reset(chat_id)
                    return
                camp_id = data['camp_id']
                groups = data['groups']

                # Extraer ID de grupo y opcionalmente el topic de la etiqueta
                match = re.search(r"\(([-\d]+)\)(?: \(topic (\d+)\))?$", message_text)
                selected = None
                if match:
                    sel_group_id = match.group(1)
                    sel_topic_id = int(match.group(2)) if match.group(2) else None
                    selected = next(
                        (
                            g for g in groups
                            if str(g['group_id']) == sel_group_id and (g.get('topic_id') or None) == sel_topic_id
                        ),
                        None
                    )
                if not selected:
                    bot.send_message(chat_id, 'Selección inválida. Intente nuevamente.')
                    return
                ok, msg = advertising.send_campaign_to_group(camp_id, selected['group_id'], selected.get('topic_id'))
                bot.send_message(chat_id, ('✅ ' if ok else '❌ ') + msg)
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                if os.path.exists(tmp):
                    os.remove(tmp)
                show_marketing_menu(chat_id)

        elif sost_num == 187:
            tmp = f'data/Temp/{chat_id}_schedule.json'
            if message_text.lower() == 'cancelar':
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                if os.path.exists(tmp):
                    os.remove(tmp)
                show_marketing_menu(chat_id)
            else:
                try:
                    with open(tmp, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except FileNotFoundError:
                    cancel_and_reset(chat_id)
                    return

                ids = None
                if message_text.lower() not in ('todos', '0'):
                    ids = [int(i) for i in re.findall(r"\d+", message_text)]

                if data['type'] == 'create':
                    ok, msg = advertising.schedule_campaign(
                        data['camp_id'], data['days'], data['times'], group_ids=ids
                    )
                    bot.send_message(chat_id, ('✅ ' if ok else '❌ ') + msg)
                else:
                    scheduler = CampaignScheduler(files.main_db, shop_id)
                    ok = scheduler.update_schedule(
                        data['schedule_id'], data['days'], data['times'], group_ids=ids
                    )
                    bot.send_message(chat_id, '✅ Programación actualizada' if ok else '❌ Error actualizando programación')

                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                if os.path.exists(tmp):
                    os.remove(tmp)
                show_marketing_menu(chat_id)


def ad_inline(callback_data, chat_id, message_id):
    shop_id = dop.get_shop_id(chat_id)
    if 'Volver al menú principal de administración' == callback_data:
        if dop.get_sost(chat_id) is True:
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
        user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
        if chat_id == config.admin_id:
            user_markup.row('💬 Respuestas')
        user_markup.row('📦 Surtido', '➕ Producto')
        user_markup.row('💰 Pagos')
        user_markup.row('📊 Stats', '📣 Difusión')
        user_markup.row('💸 Descuentos')
        user_markup.row('⚙️ Otros')
        bot.delete_message(chat_id, message_id)
        bot.send_message(chat_id, '¡Has ingresado al panel de administración del bot!\nPara salir, presiona /start', reply_markup=user_markup)

    elif callback_data == 'Volver a Marketing':
        if dop.get_sost(chat_id) is True:
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
        bot.delete_message(chat_id, message_id)
        show_marketing_menu(chat_id)

    elif callback_data == 'GLOBAL_CANCEL':
        prev = get_prev(chat_id)
        clear_state(chat_id)
        bot.delete_message(chat_id, message_id)
        route_cancel(chat_id, prev)

    elif callback_data == 'admin_telethon_config' or callback_data.startswith('global_'):
        bot.delete_message(chat_id, message_id)
        telethon_config.global_telethon_config(callback_data, chat_id)

    elif callback_data.startswith('EDIT_CAMPAIGN_'):
        camp_id = int(callback_data.split('_')[-1])
        path = f'data/Temp/{chat_id}_edit_campaign.txt'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(str(camp_id))
        key = telebot.types.InlineKeyboardMarkup()
        key.add(
            telebot.types.InlineKeyboardButton(
                text='Cancelar y volver a Marketing',
                callback_data='Volver a Marketing'
            )
        )
        bot.send_message(chat_id, (
            'Envía el nuevo texto o la nueva multimedia para la campaña.'
            '\nLuego se solicitarán los botones.'
        ), reply_markup=key)
        with shelve.open(files.sost_bd) as bd:
            bd[str(chat_id)] = 165

    elif callback_data.startswith('DELETE_SCHEDULE_'):
        schedule_id = int(callback_data.split('_')[-1])
        conn = db.get_db_connection()
        cur = conn.cursor()
        
        # Verificar que la programación existe
        cur.execute(
            'SELECT c.name FROM campaign_schedules cs JOIN campaigns c ON cs.campaign_id = c.id WHERE cs.id = ? AND cs.shop_id = ?',
            (schedule_id, shop_id),
        )
        row = cur.fetchone()
        
        if row is None:
            conn.close()
            bot.send_message(chat_id, '❌ Programación no encontrada')
        else:
            campaign_name = row[0]
            # Eliminar la programación permanentemente
            cur.execute(
                'DELETE FROM campaign_schedules WHERE id = ? AND shop_id = ?',
                (schedule_id, shop_id),
            )
            conn.commit()
            conn.close()
            bot.edit_message_reply_markup(chat_id, message_id)
            bot.send_message(chat_id, f'🗑️ Programación {schedule_id} de "{campaign_name}" eliminada permanentemente.')
        
        show_marketing_menu(chat_id)

    elif callback_data.startswith('TOGGLE_SCHEDULE_'):
        schedule_id = int(callback_data.split('_')[-1])
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'SELECT is_active FROM campaign_schedules WHERE id = ? AND shop_id = ?',
            (schedule_id, shop_id),
        )
        row = cur.fetchone()
        if row is None:
            conn.close()
            bot.send_message(chat_id, '❌ Programación no encontrada')
        else:
            new_state = 0 if row[0] else 1
            cur.execute(
                'UPDATE campaign_schedules SET is_active = ? WHERE id = ? AND shop_id = ?',
                (new_state, schedule_id, shop_id),
            )
            conn.commit()
            conn.close()
            bot.edit_message_reply_markup(chat_id, message_id)
            msg = 'Programación cancelada' if new_state == 0 else 'Programación reactivada'
            bot.send_message(chat_id, f'✅ {msg}')
        show_marketing_menu(chat_id)

    elif callback_data.startswith('EDIT_SCHEDULE_'):
        schedule_id = int(callback_data.split('_')[-1])
        path = f'data/Temp/{chat_id}_edit_schedule.txt'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(str(schedule_id))
        key = telebot.types.InlineKeyboardMarkup()
        key.add(
            telebot.types.InlineKeyboardButton(
                text='Cancelar y volver a Marketing',
                callback_data='Volver a Marketing',
            )
        )
        bot.edit_message_reply_markup(chat_id, message_id)
        bot.send_message(
            chat_id,
            'Envía los nuevos días y horas en formato "lunes,martes 10:00 12:00"',
            reply_markup=key,
        )
        with shelve.open(files.sost_bd) as bd:
            bd[str(chat_id)] = 186

    elif callback_data == 'SKIP_NEW_MEDIA':
        key = telebot.types.InlineKeyboardMarkup()
        key.add(
            telebot.types.InlineKeyboardButton(
                text='Cancelar y volver al menú principal de administración',
                callback_data='Volver al menú principal de administración'
            )
        )
        bot.edit_message_reply_markup(chat_id, message_id)
        bot.send_message(chat_id, 'Ingrese el nombre del nuevo producto', reply_markup=key)
        with shelve.open(files.sost_bd) as bd:
            bd[str(chat_id)] = 2

    elif callback_data == 'SKIP_START_MEDIA':
        text_path = f'data/Temp/{chat_id}_start_text.txt'
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                start_text = f.read()
        except FileNotFoundError:
            cancel_and_reset(chat_id)
            return
        saved = dop.save_message('start', start_text)
        bot.edit_message_reply_markup(chat_id, message_id)
        bot.send_message(chat_id, 'Mensaje de inicio actualizado.' if saved else '❌ Error guardando mensaje')
        if saved:
            with shelve.open(files.sost_bd) as bd:
                del bd[str(chat_id)]
            in_adminka(chat_id, '⚙️ Otros', None, None)
        try:
            os.remove(text_path)
        except Exception:
            pass

    elif callback_data == 'CONFIRM_BROADCAST':
        try:
            with open('data/Temp/' + str(chat_id) + '.txt', encoding='utf-8') as f:
                lines = f.read().splitlines()
            group = lines[0]
            amount = int(lines[1])
            text = lines[2]
        except Exception:
            cancel_and_reset(chat_id)
            return

        media = None
        media_path = f'data/Temp/{chat_id}_broadcast_media.txt'
        if os.path.exists(media_path):
            with open(media_path, 'r', encoding='utf-8') as f:
                mlines = f.read().splitlines()
                if len(mlines) >= 2:
                    fid = mlines[0]
                    mtype = mlines[1]
                    cap = mlines[2] if len(mlines) > 2 else None
                    media = {'file_id': fid, 'type': mtype, 'caption': cap}

        result = dop.broadcast_message(group, amount, text, media, shop_id)
        bot.edit_message_reply_markup(chat_id, message_id)
        bot.send_message(chat_id, result)
        try:
            os.remove('data/Temp/' + str(chat_id) + '.txt')
            if os.path.exists(media_path):
                os.remove(media_path)
        except Exception:
            pass

    elif callback_data == 'Añadir producto a la tienda':
        try:
            with open('data/Temp/' + str(chat_id) + 'good_name.txt', encoding='utf-8') as f:
                name = f.read()
            with open('data/Temp/' + str(chat_id) + 'good_description.txt', encoding='utf-8') as f:
                description = f.read()
            with open('data/Temp/' + str(chat_id) + 'good_format.txt', encoding='utf-8') as f:
                format_type = f.read()
            with open('data/Temp/' + str(chat_id) + 'good_manual.txt', encoding='utf-8') as f:
                manual_flag = f.read().strip()
            with open('data/Temp/' + str(chat_id) + 'good_minimum.txt', encoding='utf-8') as f:
                minimum = f.read()
            with open('data/Temp/' + str(chat_id) + 'good_price.txt', encoding='utf-8') as f:
                price = f.read()
            with open('data/Temp/' + str(chat_id) + 'good_duration.txt', encoding='utf-8') as f:
                duration_days = f.read()
            try:
                duration_days = int(duration_days)
            except ValueError:
                duration_days = 0
        except FileNotFoundError:
            cancel_and_reset(chat_id)
            bot.delete_message(chat_id, message_id)
            return

        media_temp = 'data/Temp/' + str(chat_id) + 'new_media.txt'
        media_id = None
        media_type = None
        media_caption = None
        if os.path.exists(media_temp):
            with open(media_temp, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
                if len(lines) >= 2:
                    media_id = lines[0]
                    media_type = lines[1]
                    media_caption = lines[2] if len(lines) > 2 else None

        if manual_flag == '1':
            format_type = 'manual'
            try:
                with open('data/Temp/' + str(chat_id) + 'good_manual_stock.txt', encoding='utf-8') as f:
                    manual_stock = int(f.read())
            except Exception:
                manual_stock = 0
        category_id = None
        try:
            with open('data/Temp/' + str(chat_id) + 'good_category.txt', encoding='utf-8') as f:
                category_id = int(f.read())
        except Exception:
            pass

        dop.create_product(
            name,
            description,
            format_type,
            minimum,
            price,
            f'data/goods/{shop_id}_{name}.txt',
            additional_description='',
            media_file_id=media_id,
            media_type=media_type,
            media_caption=media_caption,
            duration_days=duration_days,
            manual_delivery=int(manual_flag),
            manual_stock=manual_stock if manual_flag == '1' else 0,
            category_id=category_id,
            shop_id=shop_id,
        )
        goods_file = f"data/goods/{shop_id}_{name}.txt"
        if manual_flag != '1':
            open(goods_file, "a", encoding="utf-8").close()
        # Mostrar información del producto con la multimedia que se haya adjuntado
        media_info = dop.get_product_media(name, shop_id)
        caption = dop.format_product_with_media(name, shop_id)
        if media_info:
            mtype = media_info['type']
            file_id = media_info['file_id']
            if mtype == 'photo':
                bot.send_photo(chat_id, file_id, caption=caption, parse_mode='Markdown')
            elif mtype == 'video':
                bot.send_video(chat_id, file_id, caption=caption, parse_mode='Markdown')
            elif mtype == 'document':
                bot.send_document(chat_id, file_id, caption=caption, parse_mode='Markdown')
            elif mtype == 'audio':
                bot.send_audio(chat_id, file_id, caption=caption, parse_mode='Markdown')
            elif mtype == 'animation':
                bot.send_animation(chat_id, file_id, caption=caption, parse_mode='Markdown')
            else:
                bot.send_message(chat_id, caption, parse_mode='Markdown')
        else:
            bot.send_message(chat_id, caption or name, parse_mode='Markdown')

        if os.path.exists(media_temp):
            os.remove(media_temp)
        try:
            os.remove('data/Temp/' + str(chat_id) + 'good_category.txt')
            os.remove('data/Temp/' + str(chat_id) + 'good_manual_stock.txt')
        except Exception:
            pass
        
        user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
        user_markup.row('Añadir nueva posición en el escaparate', 'Eliminar posición')
        user_markup.row('Cambiar descripción de posición', 'Cambiar precio')
        user_markup.row('Cambiar categoría')
        user_markup.row('📝 Descripción adicional')
        user_markup.row('🎬 Multimedia productos')
        user_markup.row('Volver al menú principal')
        bot.delete_message(chat_id, message_id)
        bot.send_message(chat_id, '¡Producto añadido con éxito!', reply_markup=user_markup)


def handle_multimedia(message):
    """Manejar archivos multimedia enviados por admin"""
    chat_id = message.chat.id
    
    try:
        with shelve.open(files.sost_bd) as bd:
            state = bd.get(str(chat_id))

        if state not in (32, 200, 42, 162, 165, 305, 501):
            return

        if state == 32:
            temp_path = 'data/Temp/' + str(chat_id) + 'media_product.txt'
        elif state == 42:
            temp_path = 'data/Temp/' + str(chat_id) + '.txt'
        elif state == 162:
            temp_path = None
            media_path = f'data/Temp/{chat_id}_campaign_media.txt'
        elif state == 165:
            temp_path = None
        elif state == 305:
            temp_path = None
        else:
            temp_path = 'data/Temp/' + str(chat_id) + 'new_media.txt'

        product_name = None
        if state == 32:
            try:
                with open(temp_path, 'r', encoding='utf-8') as f:
                    product_name = f.read()
            except FileNotFoundError:
                cancel_and_reset(chat_id)
                return

        file_id = None
        media_type = None
        caption = message.caption if message.caption else None

        if message.photo:
            file_id = message.photo[-1].file_id
            media_type = 'photo'
        elif message.video:
            file_id = message.video.file_id
            media_type = 'video'
        elif message.document:
            file_id = message.document.file_id
            media_type = 'document'
        elif message.audio:
            file_id = message.audio.file_id
            media_type = 'audio'
        elif message.animation:
            file_id = message.animation.file_id
            media_type = 'animation'
                
        if file_id and media_type:
            shop_id = dop.get_shop_id(chat_id)
            if state == 32:
                saved = dop.save_product_media(product_name, file_id, media_type, caption, shop_id)
                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                user_markup.row('🎬 Multimedia productos')
                user_markup.row('Volver al menú principal')
            elif state == 42:
                try:
                    with open('data/Temp/' + str(chat_id) + '.txt', encoding='utf-8') as f:
                        lines = f.read().splitlines()
                    group = lines[0]
                    amount = int(lines[1])
                    text = lines[2]
                except (FileNotFoundError, ValueError, IndexError):
                    cancel_and_reset(chat_id)
                    return

                media_path = f"data/Temp/{chat_id}_broadcast_media.txt"
                with open(media_path, 'w', encoding='utf-8') as f:
                    f.write(file_id + '\n')
                    f.write(media_type + '\n')
                    if caption:
                        f.write(caption)

                key = telebot.types.InlineKeyboardMarkup()
                key.add(
                    telebot.types.InlineKeyboardButton(text='✅ Enviar boletín', callback_data='CONFIRM_BROADCAST')
                )
                key.add(
                    telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración',
                                                       callback_data='Volver al menú principal de administración')
                )
                bot.send_message(chat_id, 'Archivo recibido. ¿Desea enviar el mensaje ahora?', reply_markup=key)
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                return
            elif state == 162:
                with open(media_path, 'w', encoding='utf-8') as f:
                    f.write(file_id + '\n')
                    f.write(media_type)
                bot.send_message(chat_id, 'Si deseas agregar un botón escribe:\n<texto> <url>\nEscribe "no" para continuar sin botones:')
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 163
                return
            elif state == 165:
                path = f'data/Temp/{chat_id}_edit_campaign.txt'
                data_path = f'data/Temp/{chat_id}_edit_campaign_data.json'
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        _ = int(f.read())
                except FileNotFoundError:
                    cancel_and_reset(chat_id)
                    return

                data = {'media_file_id': file_id, 'media_type': media_type}
                if caption:
                    data['message_text'] = caption
                with open(data_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)

                bot.send_message(chat_id, 'Si deseas agregar un botón escribe:\n<texto> <url>\nEscribe "no" para continuar sin botones:')
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 166
                return
            elif state == 305:
                dop.update_shop_info(shop_id, media_file_id=file_id, media_type=media_type)
                bot.send_message(chat_id, 'Multimedia de tienda actualizada.')
                with shelve.open(files.sost_bd) as bd:
                    del bd[str(chat_id)]
                in_adminka(chat_id, '⚙️ Otros', None, None)
                return
            elif state == 501:
                text_path = f'data/Temp/{chat_id}_start_text.txt'
                try:
                    with open(text_path, 'r', encoding='utf-8') as f:
                        start_text = f.read()
                except FileNotFoundError:
                    cancel_and_reset(chat_id)
                    return

                saved = dop.save_message('start', start_text, file_id, media_type)
                msg = 'Mensaje de inicio actualizado.' if saved else '❌ Error guardando mensaje'
                bot.send_message(chat_id, msg)
                if saved:
                    with shelve.open(files.sost_bd) as bd:
                        del bd[str(chat_id)]
                    in_adminka(chat_id, '⚙️ Otros', None, None)
                try:
                    os.remove(text_path)
                except Exception:
                    pass
                return
            else:
                with open('data/Temp/' + str(chat_id) + 'new_media.txt', 'w', encoding='utf-8') as f:
                    f.write(file_id + '\n')
                    f.write(media_type + '\n')
                    if caption:
                        f.write(caption)
                key = telebot.types.InlineKeyboardMarkup()
                key.add(telebot.types.InlineKeyboardButton(text='Cancelar y volver al menú principal de administración', callback_data='Volver al menú principal de administración'))
                bot.send_message(chat_id, 'Ingrese el nombre del nuevo producto', reply_markup=key)
                with shelve.open(files.sost_bd) as bd:
                    bd[str(chat_id)] = 2
                return

            media_names = {
                'photo': '📸 Imagen',
                'video': '🎥 Video',
                'document': '📄 Documento',
                'audio': '🎵 Audio',
                'animation': '🎬 GIF'
            }

            if saved:
                bot.send_message(
                    chat_id,
                    f'✅ {media_names.get(media_type, "Archivo")} agregado al producto: {product_name}',
                    reply_markup=user_markup,
                )
                with shelve.open(files.sost_bd) as bd:
                    if str(chat_id) in bd:
                        del bd[str(chat_id)]
            else:
                bot.send_message(chat_id, '❌ Error guardando multimedia')
        else:
            bot.send_message(chat_id, '❌ Tipo de archivo no soportado. Envía: foto, video, documento, audio o GIF')
    except Exception:
        logging.error('Unhandled exception in handle_multimedia', exc_info=True)


def handle_cancel_command(message):
    """Manejar el comando /cancel"""
    chat_id = message.chat.id if hasattr(message, 'chat') else message
    prev = get_prev(chat_id)
    clear_state(chat_id)
    bot.send_message(chat_id, 'Operación cancelada.')
    route_cancel(chat_id, prev)