import sqlite3
import os

SQL_TABLES = [
    """CREATE TABLE IF NOT EXISTS campaigns (
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
    )""",
    """CREATE TABLE IF NOT EXISTS campaign_schedules (
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
        FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
    )""",
    """CREATE TABLE IF NOT EXISTS target_groups (
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
    )""",
    """CREATE TABLE IF NOT EXISTS platform_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT UNIQUE,
        config_data TEXT,
        is_active INTEGER DEFAULT 1,
        last_updated TEXT,
        shop_id INTEGER DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS send_logs (
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
    )""",
    """CREATE TABLE IF NOT EXISTS daily_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE,
        total_sent INTEGER DEFAULT 0,
        telegram_sent INTEGER DEFAULT 0,
        success_rate REAL DEFAULT 0,
        failed_count INTEGER DEFAULT 0,
        avg_response_time REAL DEFAULT 0,
        shop_id INTEGER DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS rate_limit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT,
        success INTEGER,
        timestamp TEXT,
        shop_id INTEGER DEFAULT 1
    )"""
]


def setup_database():
    conn = sqlite3.connect('data/db/main_data.db')
    cursor = conn.cursor()
    for sql in SQL_TABLES:
        cursor.execute(sql)
    conn.commit()
    conn.close()
    print("✅ Base de datos configurada")


def create_directories():
    directories = [
        'advertising_system',
        'data/campaigns',
        'data/logs'
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Directorio creado: {directory}")


def setup_cron():
    cron_command = f"*/5 * * * * cd {os.getcwd()} && python3 advertising_cron.py"
    print("📅 Agregar a crontab:")
    print(cron_command)
    print("\nEjecutar: crontab -e")


if __name__ == '__main__':
    print("🚀 Configurando sistema de publicidad...")
    setup_database()
    create_directories()
    setup_cron()
    print("✅ Configuración completada")
