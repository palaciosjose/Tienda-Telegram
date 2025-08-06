#!/usr/bin/env python3
"""Utility script to reset local data directory and reinitialize the databases."""

import os
import shutil
import sqlite3

import init_db


def setup_discount_system():
    """Configura el sistema de descuentos sin dependencias externas"""
    print("🔧 Configurando sistema de descuentos...")
    
    try:
        conn = sqlite3.connect('data/db/main_data.db')
        cursor = conn.cursor()
        
        # Crear tabla de configuración de descuentos (ya incluye shop_id)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discount_config (
                id INTEGER PRIMARY KEY,
                discount_enabled INTEGER DEFAULT 1,
                discount_text TEXT DEFAULT '🔥 DESCUENTOS ESPECIALES ACTIVOS 🔥',
                discount_multiplier REAL DEFAULT 1.5,
                show_fake_price INTEGER DEFAULT 1,
                shop_id INTEGER UNIQUE
            )
        ''')
        
        # Verificar si ya existe configuración para shop_id=1
        cursor.execute("SELECT COUNT(*) FROM discount_config WHERE shop_id = 1")
        if cursor.fetchone()[0] == 0:
            # Insertar configuración inicial (ahora con shop_id)
            cursor.execute("""
                INSERT INTO discount_config (discount_enabled, discount_text, discount_multiplier, show_fake_price, shop_id)
                VALUES (1, '🔥 DESCUENTOS ESPECIALES ACTIVOS 🔥', 1.5, 1, 1)
            """)
            print("✅ Configuración inicial de descuentos creada")
        else:
            print("ℹ️ La configuración de descuentos ya existe")
        
        conn.commit()
        conn.close()
        
        print("✅ Sistema de descuentos configurado correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error configurando descuentos: {e}")
        return False


def setup_advertising_system():
    """Configura el sistema de publicidad sin dependencias externas"""
    print("🔧 Configurando sistema de publicidad...")
    
    try:
        # Las tablas de publicidad ya se crean en init_db.py, solo verificamos
        conn = sqlite3.connect('data/db/main_data.db')
        cursor = conn.cursor()
        
        # Verificar que las tablas de publicidad existen
        tables_to_check = ['campaigns', 'target_groups', 'send_logs', 'daily_stats']
        for table in tables_to_check:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cursor.fetchone():
                print(f"✅ Tabla '{table}' verificada")
            else:
                print(f"⚠️ Tabla '{table}' no encontrada")
        
        conn.close()
        print("✅ Sistema de publicidad verificado")
        
        # Crear directorios necesarios
        directories = [
            'advertising_system',
            'data/campaigns', 
            'data/logs'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Directorio creado: {directory}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error configurando publicidad: {e}")
        return False


def main():
    """Función principal del reset"""
    print("🔄 RESET DE DATOS - Tienda Telegram")
    print("=" * 50)
    
    if os.path.exists('data'):
        confirm = input("This will delete the 'data/' directory. Continue? [y/N]: ").strip().lower()
        if confirm != 'y':
            print('❌ Operation cancelled.')
            return
        
        shutil.rmtree('data')
        print("✅ 'data/' directory removed")
    
    print("\n🏗️ Recreando estructura...")
    
    # Paso 1: Crear base de datos y estructura básica
    init_db.create_database()
    
    # Paso 2: Configurar sistema de descuentos
    setup_discount_system()
    
    # Paso 3: Configurar sistema de publicidad
    setup_advertising_system()
    
    print("\n🎉 ¡Reset completado exitosamente!")
    print("\n📋 Próximos pasos:")
    print("1. Configura tu archivo .env con tus tokens")
    print("2. Ejecuta: python main.py")
    print("3. Envía /start al bot para configuración inicial")
    print("4. Configura métodos de pago desde el panel de admin")
    
    print("\n✨ Sistema reseteado incluye:")
    print("• 🏪 Soporte para múltiples tiendas")
    print("• 💰 Sistema de pagos (PayPal + Binance)")
    print("• 💸 Sistema de descuentos")
    print("• 📢 Sistema de publicidad automatizada")
    print("• 📊 Estadísticas y analytics")
    print("• 🔍 Sistema de validación de compras")


if __name__ == '__main__':
    main()
