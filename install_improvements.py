#!/usr/bin/env python3
"""
Instalador corregido de mejoras para el sistema de validación de compras
"""

import os
import shutil
import sqlite3
import sys
import db
from datetime import datetime

def backup_files():
    """Crear backup de archivos importantes"""
    print("📦 Creando backup de archivos...")
    
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        'main.py',
        'adminka.py', 
        'dop.py',
        'payments.py',
        'data/db/main_data.db'
    ]
    
    for file in files_to_backup:
        if os.path.exists(file):
            dest = os.path.join(backup_dir, os.path.basename(file))
            shutil.copy2(file, dest)
            print(f"✅ {file} → {dest}")
    
    print(f"📦 Backup creado en: {backup_dir}")
    return backup_dir

def upgrade_database():
    """Actualizar estructura de la base de datos - Versión corregida"""
    print("🔄 Actualizando base de datos...")
    
    try:
        conn = sqlite3.connect('data/db/main_data.db')
        cursor = conn.cursor()
        
        # Verificar columnas existentes
        cursor.execute("PRAGMA table_info(purchases)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Columnas actuales: {columns}")
        
        # Agregar payment_method si no existe
        if 'payment_method' not in columns:
            cursor.execute('ALTER TABLE purchases ADD COLUMN payment_method TEXT')
            print("✅ Columna 'payment_method' agregada")
        else:
            print("ℹ️ Columna 'payment_method' ya existe")
        
        # Para timestamp, usamos una estrategia diferente
        if 'timestamp' not in columns:
            # Agregar columna sin valor predeterminado
            cursor.execute('ALTER TABLE purchases ADD COLUMN timestamp TEXT')
            print("✅ Columna 'timestamp' agregada")
            
            # Actualizar registros existentes con timestamp actual
            current_time = datetime.now().isoformat()
            cursor.execute('UPDATE purchases SET timestamp = ? WHERE timestamp IS NULL', (current_time,))
            print("✅ Registros existentes actualizados con timestamp")
        else:
            print("ℹ️ Columna 'timestamp' ya existe")
        
        # Crear tabla de validación detallada
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchase_validation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                product_name TEXT,
                amount INTEGER,
                price INTEGER,
                payment_method TEXT,
                payment_id TEXT,
                timestamp TEXT,
                status TEXT DEFAULT 'completed'
            )
        ''')
        print("✅ Tabla 'purchase_validation' creada")
        
        # Crear índices para mejorar rendimiento
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases(id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchases_username ON purchases(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchases_timestamp ON purchases(timestamp)')
            print("✅ Índices de rendimiento creados")
        except:
            pass
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando base de datos: {e}")
        return False

def create_purchase_validator():
    """Crear archivo purchase_validator.py"""
    print("📝 Creando purchase_validator.py...")
    
    content = '''import sqlite3
import telebot
import files
import config
from datetime import datetime
from bot_instance import bot

def validate_purchase_by_user(user_id=None, username=None):
    """Valida las compras de un usuario específico"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT id, username, name_good, amount, price, payment_method, timestamp 
                FROM purchases 
                WHERE id = ?
                ORDER BY rowid DESC
            """, (user_id,))
        elif username:
            clean_username = username.replace('@', '')
            cursor.execute("""
                SELECT id, username, name_good, amount, price, payment_method, timestamp 
                FROM purchases 
                WHERE username = ?
                ORDER BY rowid DESC
            """, (clean_username,))
        else:
            return "❌ Debes proporcionar user_id o username"
        
        purchases = cursor.fetchall()
        
        if not purchases:
            return "❌ No se encontraron compras para este usuario"
        
        response = f"📋 **Historial de compras validado:**\\n\\n"
        total_spent = 0
        
        for i, purchase in enumerate(purchases, 1):
            user_id, username, product, amount, price, payment_method, timestamp = purchase
            total_spent += price
            
            # Formatear timestamp
            time_str = "Fecha no disponible"
            if timestamp:
                try:
                    if 'T' in timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime("%d/%m/%Y %H:%M")
                    else:
                        time_str = str(timestamp)
                except:
                    time_str = str(timestamp)
            
            response += f"🛒 **Compra #{i}**\\n"
            response += f"📦 **Producto:** {product}\\n"
            response += f"🔢 **Cantidad:** {amount}\\n"
            response += f"💰 **Precio:** ${price} USD\\n"
            response += f"💳 **Método:** {payment_method or 'No especificado'}\\n"
            response += f"📅 **Fecha:** {time_str}\\n"
            response += f"👤 **ID:** `{user_id}`\\n"
            response += f"📱 **Username:** @{username}\\n"
            response += "━━━━━━━━━━━━━━━━━━━━\\n\\n"
        
        response += f"💎 **Total gastado:** ${total_spent} USD\\n"
        response += f"🛍️ **Total compras:** {len(purchases)}"
        
        return response
        
    except Exception as e:
        return f"❌ Error consultando base de datos: {e}"

def get_purchase_stats():
    """Obtiene estadísticas de compras"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        
        # Estadísticas generales
        cursor.execute("SELECT COUNT(*), SUM(price), COUNT(DISTINCT id) FROM purchases")
        result = cursor.fetchone()
        total_purchases, total_revenue, unique_buyers = result if result else (0, 0, 0)
        
        # Top productos
        cursor.execute("""
            SELECT name_good, COUNT(*) as sales, SUM(price) as revenue 
            FROM purchases 
            GROUP BY name_good 
            ORDER BY sales DESC 
            LIMIT 5
        """)
        top_products = cursor.fetchall()
        
        # Métodos de pago
        cursor.execute("""
            SELECT payment_method, COUNT(*), SUM(price) 
            FROM purchases 
            WHERE payment_method IS NOT NULL AND payment_method != ''
            GROUP BY payment_method
        """)
        payment_methods = cursor.fetchall()
        
        
        response = "📊 **Estadísticas de Ventas:**\\n\\n"
        response += f"🛍️ **Total compras:** {total_purchases or 0}\\n"
        response += f"💰 **Ingresos totales:** ${total_revenue or 0} USD\\n"
        response += f"👥 **Compradores únicos:** {unique_buyers or 0}\\n\\n"
        
        if top_products:
            response += "🏆 **Top Productos:**\\n"
            for product, sales, revenue in top_products:
                response += f"• {product}: {sales} ventas (${revenue} USD)\\n"
        
        if payment_methods:
            response += "\\n💳 **Métodos de Pago:**\\n"
            for method, count, revenue in payment_methods:
                method_name = method or "No especificado"
                response += f"• {method_name}: {count} transacciones (${revenue} USD)\\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error: {e}"

def search_recent_purchases(hours=24):
    """Busca compras recientes"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        
        # Para SQLite, usamos una aproximación con rowid
        cursor.execute(f"""
            SELECT id, username, name_good, amount, price, payment_method, timestamp 
            FROM purchases 
            ORDER BY rowid DESC 
            LIMIT 50
        """)
        
        purchases = cursor.fetchall()
        
        if not purchases:
            return f"❌ No hay compras recientes"
        
        response = f"📊 **Compras recientes:**\\n\\n"
        total = 0
        
        for purchase in purchases:
            user_id, username, product, amount, price, payment_method, timestamp = purchase
            total += price
            
            time_str = ""
            if timestamp:
                try:
                    if 'T' in timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime("%H:%M")
                    else:
                        time_str = str(timestamp)[:10]
                except:
                    time_str = "N/A"
            
            response += f"🛒 @{username} - {product} x{amount} - ${price} ({payment_method or 'N/A'}) {time_str}\\n"
        
        response += f"\\n💰 **Total:** ${total} USD | 🛍️ **Ventas:** {len(purchases)}"
        return response
        
    except Exception as e:
        return f"❌ Error: {e}"
'''
    
    with open('purchase_validator.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ purchase_validator.py creado")

def update_dop_file():
    """Actualizar dop.py con nuevas funciones"""
    print("📝 Actualizando dop.py...")
    
    # Leer archivo actual
    with open('dop.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar si ya tiene las funciones
    if 'new_buy_improved' in content:
        print("ℹ️ dop.py ya contiene las funciones actualizadas")
        return
    
    # Nuevas funciones a agregar
    new_functions = '''
def new_buy_improved(his_id, username, name_good, amount, price, payment_method="Unknown", payment_id=None):
    """Versión mejorada de new_buy que incluye método de pago y timestamp"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        
        # Usar timestamp actual
        from datetime import datetime
        current_time = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO purchases 
            (id, username, name_good, amount, price, payment_method, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (his_id, username, name_good, amount, price, payment_method, current_time))
        
        # También insertar en tabla de validación si existe
        try:
            cursor.execute("""
                INSERT INTO purchase_validation 
                (user_id, username, product_name, amount, price, payment_method, payment_id, timestamp, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed')
            """, (his_id, username, name_good, amount, price, payment_method, payment_id, current_time))
        except:
            pass  # Si la tabla no existe, continuar
        
        con.commit()
        return True
    except Exception as e:
        print(f"Error en new_buy_improved: {e}")
        return False

def get_daily_sales():
    """Obtiene las ventas del día actual"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        
        # Obtener ventas recientes (aproximación por rowid)
        cursor.execute("""
            SELECT COUNT(*), SUM(price)
            FROM purchases 
            ORDER BY rowid DESC 
            LIMIT 100
        """)
        
        count, total = cursor.fetchone()
        
        cursor.execute("""
            SELECT name_good, COUNT(*), SUM(price)
            FROM purchases 
            GROUP BY name_good
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        
        products = cursor.fetchall()
        
        response = "📊 **Estadísticas de Ventas:**\\n\\n"
        response += f"🛍️ **Transacciones recientes:** {count or 0}\\n"
        response += f"💰 **Ingresos totales:** ${total or 0} USD\\n\\n"
        
        if products:
            response += "📦 **Productos más vendidos:**\\n"
            for product, qty, revenue in products:
                response += f"• {product}: {qty} ventas (${revenue} USD)\\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error: {e}"

def search_user_purchases(search_term):
    """Busca compras por ID de usuario o username"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        
        # Si es número, buscar por ID
        if search_term.isdigit():
            cursor.execute("""
                SELECT id, username, name_good, amount, price, payment_method, timestamp 
                FROM purchases 
                WHERE id = ?
                ORDER BY rowid DESC
            """, (int(search_term),))
        else:
            # Si no, buscar por username
            clean_username = search_term.replace('@', '')
            cursor.execute("""
                SELECT id, username, name_good, amount, price, payment_method, timestamp 
                FROM purchases 
                WHERE username LIKE ?
                ORDER BY rowid DESC
            """, (f"%{clean_username}%",))
        
        purchases = cursor.fetchall()
        
        if not purchases:
            return "❌ No se encontraron compras para este usuario"
        
        # Formatear respuesta
        response = f"📋 **Compras encontradas para: {search_term}**\\n\\n"
        total_spent = 0
        
        for i, purchase in enumerate(purchases, 1):
            user_id, username, product, amount, price, payment_method, timestamp = purchase
            total_spent += price
            
            # Formatear fecha
            try:
                if timestamp and 'T' in timestamp:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp)
                    date_str = dt.strftime("%d/%m/%Y %H:%M")
                else:
                    date_str = str(timestamp) if timestamp else "Fecha no disponible"
            except:
                date_str = str(timestamp) if timestamp else "Fecha no disponible"
            
            response += f"🛒 **Compra #{i}**\\n"
            response += f"📦 {product} x{amount}\\n"
            response += f"💰 ${price} USD\\n"
            response += f"💳 {payment_method or 'No especificado'}\\n"
            response += f"📅 {date_str}\\n"
            response += f"👤 ID: `{user_id}` | @{username}\\n"
            response += "━━━━━━━━━━━━━━━━━━━━\\n\\n"
        
        response += f"💎 **Total gastado:** ${total_spent} USD\\n"
        response += f"🛍️ **Total compras:** {len(purchases)}"
        
        return response
        
    except Exception as e:
        return f"❌ Error buscando compras: {e}"
'''
    
    # Agregar las nuevas funciones al final
    content += new_functions
    
    with open('dop.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ dop.py actualizado con nuevas funciones")

def update_adminka_file():
    """Actualizar adminka.py con el nuevo menú"""
    print("📝 Actualizando adminka.py...")
    
    # Leer archivo actual
    with open('adminka.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar si ya tiene las actualizaciones
    if '🔍 Validar Compras' in content:
        print("ℹ️ adminka.py ya contiene las actualizaciones")
        return
    
    # Agregar import
    if 'import purchase_validator' not in content:
        import_line = "import purchase_validator\\n"
        content = content.replace("import config, dop, files", "import config, dop, files\\n" + import_line)
    
    # Buscar y reemplazar el menú principal
    old_menu = """user_markup.row('Estadísticas', 'Boletín informativo')
            user_markup.row('Otras configuraciones')"""
    
    new_menu = """user_markup.row('Estadísticas', 'Boletín informativo')
            user_markup.row('🔍 Validar Compras', 'Otras configuraciones')"""
    
    content = content.replace(old_menu, new_menu)
    
    # Agregar las nuevas opciones del menú
    new_menu_options = '''
        elif '🔍 Validar Compras' == message_text:
            user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
            user_markup.row('🔎 Buscar por ID usuario', '🔎 Buscar por username')
            user_markup.row('📊 Ventas generales', '📈 Estadísticas detalladas')
            user_markup.row('🕐 Compras recientes')
            user_markup.row('Volver al menú principal')
            bot.send_message(chat_id, '🔍 **Panel de Validación de Compras**\\n\\nSelecciona una opción para buscar y validar compras:', reply_markup=user_markup, parse_mode='Markdown')

        elif '🔎 Buscar por ID usuario' == message_text:
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, '🔎 **Buscar por ID de Usuario**\\n\\nEnvía el ID de Telegram del usuario (número):', reply_markup=key, parse_mode='Markdown')
            with shelve.open(files.sost_bd) as bd: bd[str(chat_id)] = 50

        elif '🔎 Buscar por username' == message_text:
            key = telebot.types.InlineKeyboardMarkup()
            key.add(telebot.types.InlineKeyboardButton(text='Cancelar', callback_data='Volver al menú principal de administración'))
            bot.send_message(chat_id, '🔎 **Buscar por Username**\\n\\nEnvía el username del usuario (con o sin @):', reply_markup=key, parse_mode='Markdown')
            with shelve.open(files.sost_bd) as bd: bd[str(chat_id)] = 51

        elif '📊 Ventas generales' == message_text:
            result = dop.get_daily_sales()
            bot.send_message(chat_id, result, parse_mode='Markdown')

        elif '📈 Estadísticas detalladas' == message_text:
            result = purchase_validator.get_purchase_stats()
            bot.send_message(chat_id, result, parse_mode='Markdown')

        elif '🕐 Compras recientes' == message_text:
            result = purchase_validator.search_recent_purchases(24)
            bot.send_message(chat_id, result, parse_mode='Markdown')
'''
    
    # Buscar dónde insertar las nuevas opciones
    insert_point = content.find("elif 'Otras configuraciones' == message_text:")
    if insert_point != -1:
        content = content[:insert_point] + new_menu_options + "\\n        " + content[insert_point:]
    
    # Agregar los nuevos estados al final de la función
    new_states = '''
            elif sost_num == 50:  # Buscar por ID
                try:
                    user_id = int(message_text)
                    result = purchase_validator.validate_purchase_by_user(user_id=user_id)
                    bot.send_message(chat_id, result, parse_mode='Markdown')
                    
                    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                    user_markup.row('🔎 Buscar por ID usuario', '🔎 Buscar por username')
                    user_markup.row('📊 Ventas generales', '📈 Estadísticas detalladas')
                    user_markup.row('🕐 Compras recientes')
                    user_markup.row('Volver al menú principal')
                    bot.send_message(chat_id, '✅ Búsqueda completada. ¿Qué más deseas hacer?', reply_markup=user_markup)
                    
                    with shelve.open(files.sost_bd) as bd: del bd[str(chat_id)]
                except ValueError:
                    bot.send_message(chat_id, '❌ El ID debe ser un número. Intenta de nuevo:')

            elif sost_num == 51:  # Buscar por username
                result = purchase_validator.validate_purchase_by_user(username=message_text)
                bot.send_message(chat_id, result, parse_mode='Markdown')
                
                user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
                user_markup.row('🔎 Buscar por ID usuario', '🔎 Buscar por username')
                user_markup.row('📊 Ventas generales', '📈 Estadísticas detalladas')
                user_markup.row('🕐 Compras recientes')
                user_markup.row('Volver al menú principal')
                bot.send_message(chat_id, '✅ Búsqueda completada. ¿Qué más deseas hacer?', reply_markup=user_markup)
                
                with shelve.open(files.sost_bd) as bd: del bd[str(chat_id)]
'''
    
    # Buscar el último elif sost_num e insertar los nuevos estados
    last_elif_pos = content.rfind("elif sost_num ==")
    if last_elif_pos != -1:
        # Encontrar el final de ese bloque
        next_def_pos = content.find("def ", last_elif_pos)
        if next_def_pos != -1:
            content = content[:next_def_pos] + new_states + "\\n\\n" + content[next_def_pos:]
        else:
            content += new_states
    
    with open('adminka.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ adminka.py actualizado con nuevo menú")

def main():
    """Función principal del instalador corregido"""
    print("🚀 Instalador de Mejoras para Sistema de Validación de Compras (Versión Corregida)")
    print("=" * 80)
    
    # Verificar archivos necesarios
    required_files = ['main.py', 'dop.py', 'adminka.py', 'payments.py']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Archivos faltantes: {', '.join(missing_files)}")
        print("Asegúrate de ejecutar este script en el directorio del bot.")
        return
    
    print("✅ Todos los archivos necesarios encontrados")
    
    try:
        # Paso 1: Backup
        backup_dir = backup_files()
        
        # Paso 2: Actualizar base de datos (versión corregida)
        if not upgrade_database():
            print("❌ Error actualizando base de datos. Revisa el backup.")
            return
        
        # Paso 3: Crear archivos nuevos
        create_purchase_validator()
        
        # Paso 4: Actualizar archivos existentes
        update_dop_file()
        update_adminka_file()
        
        print("\\n🎉 ¡Instalación completada exitosamente!")
        print("\\n📋 Próximos pasos:")
        print("1. Reinicia tu bot: python3 main.py")
        print("2. Ve al panel de admin: /adm")
        print("3. Verás la nueva opción: '🔍 Validar Compras'")
        print("4. El backup está en:", backup_dir)
        
        print("\\n✨ Nuevas funciones disponibles:")
        print("• 🔎 Buscar compras por ID de usuario")
        print("• 🔎 Buscar compras por username") 
        print("• 📊 Ver estadísticas de ventas")
        print("• 📈 Estadísticas detalladas de productos")
        print("• 🕐 Ver compras recientes")
        print("• 💾 Registro mejorado con timestamps")
        print("• 💳 Registro de método de pago")
        
        print("\\n🛡️ Para validar reclamos:")
        print("1. Un cliente reclama → /adm → 🔍 Validar Compras")
        print("2. Buscar por su ID o username")
        print("3. Ver historial completo con fechas y métodos")
        print("4. Validar o refutar el reclamo con evidencia")
        
    except Exception as e:
        print(f"❌ Error durante la instalación: {e}")
        print(f"Puedes restaurar desde el backup: {backup_dir}")

if __name__ == '__main__':
    main()