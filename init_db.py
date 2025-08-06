#!/usr/bin/env python3
"""Script para inicializar la base de datos y estructura del proyecto."""

import sqlite3
import os


def _create_auxiliary_tables(cursor):
    """Create auxiliary tables for topics, global configuration and logs.

    The tables are created with ``IF NOT EXISTS`` so the function can be
    executed multiple times without affecting existing installations.
    """
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS store_topics (
            store_id INTEGER,
            group_id TEXT,
            group_name TEXT,
            topic_id INTEGER,
            topic_name TEXT
        )
        '''
    )
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS global_config (key TEXT PRIMARY KEY, value TEXT)'''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS unified_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            level TEXT,
            message TEXT,
            store_id INTEGER
        )
        '''
    )
    print("✓ Tablas 'store_topics', 'global_config' y 'unified_logs' creadas")


def create_database():
    print("Creando estructura de directorios...")
    
    # Crear directorios si no existen
    directories = [
        'data/db',
        'data/bd', 
        'data/lists',
        'data/goods',
        'data/Temp'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Directorio creado: {directory}")
    
    print("\nCreando base de datos...")
    
    # Crear base de datos
    conn = sqlite3.connect('data/db/main_data.db')
    cursor = conn.cursor()
    
    # Tabla de tiendas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            media_file_id TEXT,
            media_type TEXT,
            button1_text TEXT,
            button1_url TEXT,
            button2_text TEXT,
            button2_url TEXT,
            campaign_limit INTEGER DEFAULT 0,
            telethon_enabled INTEGER DEFAULT 0,
            telethon_api_id TEXT,
            telethon_api_hash TEXT,
            telethon_phone TEXT,
            telethon_bridge_group TEXT,
            telethon_daemon_status TEXT,
            telethon_last_activity TEXT,
            max_campaigns_daily INTEGER DEFAULT 0,
            current_campaigns_today INTEGER DEFAULT 0
        )
    ''')
    print("✓ Tabla 'shops' creada")

    # Tabla de categorías
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            shop_id INTEGER DEFAULT 1
        )
    ''')
    print("✓ Tabla 'categories' creada")

    # Crear tabla de productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goods (
            name TEXT,
            description TEXT,
            format TEXT,
            minimum INTEGER,
            price INTEGER,
            stored TEXT,
            additional_description TEXT DEFAULT '',
            media_file_id TEXT,
            media_type TEXT,
            media_caption TEXT,
            duration_days INTEGER DEFAULT NULL,
            manual_delivery INTEGER DEFAULT 0,
            manual_stock INTEGER DEFAULT 0,
            category_id INTEGER,
            shop_id INTEGER DEFAULT 1,
            PRIMARY KEY (name, shop_id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')
    print("✓ Tabla 'goods' creada")
    
    # Crear tabla de compras
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER,
            username TEXT,
            name_good TEXT,
            amount INTEGER,
            price INTEGER,
            shop_id INTEGER DEFAULT 1
        )
    ''')
    print("✓ Tabla 'purchases' creada")
    
    # Crear tabla de compradores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buyers (
            id INTEGER PRIMARY KEY,
            username TEXT,
            payed INTEGER,
            shop_id INTEGER DEFAULT 1
        )
    ''')
    print("✓ Tabla 'buyers' creada")

    # Tabla que relaciona usuarios con su tienda seleccionada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_users (
            user_id INTEGER PRIMARY KEY,
            shop_id INTEGER DEFAULT 1
        )
    ''')
    print("✓ Tabla 'shop_users' creada")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_ratings (
            shop_id INTEGER,
            user_id INTEGER,
            rating INTEGER,
            PRIMARY KEY (shop_id, user_id)
        )
    ''')
    print("✓ Tabla 'shop_ratings' creada")

    # Tablas para sistema de publicidad
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            message_text TEXT NOT NULL,
            media_file_id TEXT,
            media_type TEXT,
            media_caption TEXT,
            button1_text TEXT,
            button1_url TEXT,
            button2_text TEXT,
            button2_url TEXT,
            status TEXT DEFAULT 'active',
            created_date TEXT,
            created_by INTEGER,
            shop_id INTEGER DEFAULT 1,
            daily_limit INTEGER DEFAULT 3,
            priority INTEGER DEFAULT 1
        )
    ''')
    print("✓ Tabla 'campaigns' creada")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaign_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            schedule_name TEXT,
            frequency TEXT,
            schedule_json TEXT,
            target_platforms TEXT,
            is_active INTEGER DEFAULT 1,
            next_send_telegram TEXT,
            created_date TEXT,
            shop_id INTEGER DEFAULT 1,
            group_ids TEXT,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
        )
    ''')
    print("✓ Tabla 'campaign_schedules' creada")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS target_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            group_id TEXT NOT NULL,
            group_name TEXT,
            topic_id INTEGER,
            category TEXT,
            status TEXT DEFAULT 'active',
            last_sent TEXT,
            success_rate REAL DEFAULT 1.0,
            added_date TEXT,
            notes TEXT,
            shop_id INTEGER DEFAULT 1
        )
    ''')
    print("✓ Tabla 'target_groups' creada")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_groups (
            group_id TEXT PRIMARY KEY,
            group_name TEXT,
            added_date TEXT
        )
    ''')
    print("✓ Tabla 'bot_groups' creada")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS platform_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT UNIQUE,
            config_data TEXT,
            is_active INTEGER DEFAULT 1,
            last_updated TEXT,
            shop_id INTEGER DEFAULT 1
        )
    ''')
    print("✓ Tabla 'platform_config' creada")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS send_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            group_id TEXT,
            platform TEXT,
            status TEXT,
            sent_date TEXT,
            response_time REAL,
            error_message TEXT,
            shop_id INTEGER DEFAULT 1,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
        )
    ''')
    print("✓ Tabla 'send_logs' creada")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            total_sent INTEGER DEFAULT 0,
            telegram_sent INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            avg_response_time REAL DEFAULT 0,
            shop_id INTEGER DEFAULT 1
        )
    ''')
    print("✓ Tabla 'daily_stats' creada")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            success INTEGER,
            timestamp TEXT,
            shop_id INTEGER DEFAULT 1
        )
    ''')
    print("✓ Tabla 'rate_limit_logs' creada")

    _create_auxiliary_tables(cursor)

    # Crear tabla para datos de PayPal
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paypal_data (
            client_id TEXT,
            client_secret TEXT,
            sandbox INTEGER DEFAULT 1,
            shop_id INTEGER DEFAULT 1
        )
    ''')
    print("✓ Tabla 'paypal_data' creada")

    # Crear tabla para datos de Binance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS binance_data (
            api_key TEXT,
            api_secret TEXT,
            merchant_id TEXT,
            shop_id INTEGER DEFAULT 1
        )
    ''')
    print("✓ Tabla 'binance_data' creada")

    # Tabla de descuentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS discounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            percent INTEGER,
            start_time TEXT,
            end_time TEXT,
            category_id INTEGER,
            shop_id INTEGER
        )
    ''')
    print("✓ Tabla 'discounts' creada")

    # Tabla de configuración de descuentos
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
    print("✓ Tabla 'discount_config' creada")
    
    conn.commit()
    conn.close()
    
    print("\nCreando archivos de listas...")
    
    # Crear archivos de listas vacíos si no existen
    lists_files = [
        'data/lists/admins_list.txt',
        'data/lists/chatid_list.txt', 
        'data/lists/blockusers_list.txt'
    ]
    
    for file_path in lists_files:
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                pass
            print(f"✓ Archivo creado: {file_path}")
    
    # Crear archivo de log si no existe
    log_file = 'data/working_log.log'
    if not os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as f:
            pass
        print(f"✓ Archivo creado: {log_file}")
    
    print("\n🎉 ¡Base de datos y estructura creada exitosamente!")
    print("\nPróximos pasos:")
    print("1. Verifica que tu token en config.py sea correcto")
    print("2. Instala las dependencias: pip install pyTelegramBotAPI paypalrestsdk python-binance")
    print("3. Ejecuta: python main.py")
    print("4. Envía /start al bot para configuración inicial")

if __name__ == '__main__':
    create_database()
