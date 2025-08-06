#!/usr/bin/env python3
"""
Script para corregir el bucle infinito en el sistema de descuentos
"""

def fix_adminka():
    """Corregir el archivo adminka.py"""
    print("🔧 Corrigiendo bucle infinito en adminka.py...")
    
    # Leer archivo actual
    with open('adminka.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar y reemplazar la línea problemática
    old_line = "in_adminka(chat_id, 'Volver al menú principal', None, None)"
    new_line = "show_main_admin_menu(chat_id)"
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        print("✅ Línea problemática corregida")
    else:
        print("ℹ️ Línea problemática no encontrada")
    
    # Agregar la nueva función al final del archivo
    new_function = '''

def show_main_admin_menu(chat_id):
    """Mostrar menú principal de administración sin bucle"""
    if dop.get_sost(chat_id):
        with shelve.open(files.sost_bd) as bd:
            if str(chat_id) in bd:
                del bd[str(chat_id)]
    
    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
    user_markup.row('📦 Surtido', '➕ Producto')
    user_markup.row('💰 Pagos', '💸 Descuentos')
    user_markup.row('📢 Marketing', '📣 Difusión')
    user_markup.row('📊 Estadísticas', 'Boletín informativo')
    user_markup.row('🔍 Validar Compras', 'Otras configuraciones')
    user_markup.row('💬 Respuestas')
    
    bot.send_message(chat_id, '¡Panel de administración!\nPara salir: /start', reply_markup=user_markup)
'''
    
    # Verificar si la función ya existe
    if "def show_main_admin_menu(chat_id):" not in content:
        content += new_function
        print("✅ Nueva función agregada")
    else:
        print("ℹ️ La función ya existe")
    
    # Guardar archivo corregido
    with open('adminka.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Archivo adminka.py corregido")

if __name__ == '__main__':
    fix_adminka()
    print("\n🎉 ¡Corrección completada!")
    print("Reinicia el bot para aplicar los cambios:")
    print("pkill -f main.py && nohup python3 main.py > bot.log 2>&1 &")
