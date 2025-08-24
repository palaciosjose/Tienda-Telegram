import telebot, shelve, datetime, sqlite3, random, os, re
import files, config
import db
from bot_instance import bot
import logging

logging.basicConfig(level=logging.INFO)

# Flag to avoid repeated logging when initializing discounts
_discount_initialized = False


def _slugify(name):
    """Convert product name to URL-friendly slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).lower().strip("-")
    return slug


def get_product_link(product_name, shop_id):
    """Generate a deep-link URL for a product."""
    try:
        username = bot.get_me().username
    except Exception:
        username = ""
    slug = _slugify(product_name)
    return f"https://t.me/{username}?start=prod_{shop_id}_{slug}"


def get_product_by_slug(slug, shop_id=1):
    """Return product name matching the slug for the given shop."""
    for name in get_goods(shop_id):
        if _slugify(name) == slug:
            return name
    return None

# ---------------------------------------------------------------------------
# Utilidad para asegurar que la base de datos tenga las columnas necesarias
# para la descripción adicional y la gestión de multimedia. Algunas
# instalaciones antiguas pueden carecer de estas columnas y provocar errores
# "no such column" cuando se utilizan las funciones relacionadas. Esta función
# se ejecuta al importar el módulo y modifica la tabla `goods` si es necesario.
# ---------------------------------------------------------------------------
def ensure_database_schema():
    """Agregar tablas y columnas faltantes si es necesario."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()

        # Tabla de tiendas
        cursor.execute(
            """
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
                campaign_limit INTEGER DEFAULT 0
            )
            """
        )

        cursor.execute("PRAGMA table_info(shops)")
        shop_cols = [c[1] for c in cursor.fetchall()]
        if 'description' not in shop_cols:
            cursor.execute("ALTER TABLE shops ADD COLUMN description TEXT")
        if 'media_file_id' not in shop_cols:
            cursor.execute("ALTER TABLE shops ADD COLUMN media_file_id TEXT")
        if 'media_type' not in shop_cols:
            cursor.execute("ALTER TABLE shops ADD COLUMN media_type TEXT")
        if 'button1_text' not in shop_cols:
            cursor.execute("ALTER TABLE shops ADD COLUMN button1_text TEXT")
        if 'button1_url' not in shop_cols:
            cursor.execute("ALTER TABLE shops ADD COLUMN button1_url TEXT")
        if 'button2_text' not in shop_cols:
            cursor.execute("ALTER TABLE shops ADD COLUMN button2_text TEXT")
        if 'button2_url' not in shop_cols:
            cursor.execute("ALTER TABLE shops ADD COLUMN button2_url TEXT")
        if 'campaign_limit' not in shop_cols:
            cursor.execute("ALTER TABLE shops ADD COLUMN campaign_limit INTEGER DEFAULT 0")
        if 'telethon_enabled' not in shop_cols:
            cursor.execute(
                "ALTER TABLE shops ADD COLUMN telethon_enabled INTEGER DEFAULT 0"
            )
        if 'telethon_api_id' not in shop_cols:
            cursor.execute("ALTER TABLE shops ADD COLUMN telethon_api_id TEXT")
        if 'telethon_api_hash' not in shop_cols:
            cursor.execute("ALTER TABLE shops ADD COLUMN telethon_api_hash TEXT")
        if 'telethon_phone' not in shop_cols:
            cursor.execute("ALTER TABLE shops ADD COLUMN telethon_phone TEXT")
        if 'telethon_bridge_group' not in shop_cols:
            cursor.execute(
                "ALTER TABLE shops ADD COLUMN telethon_bridge_group TEXT"
            )
        if 'telethon_daemon_status' not in shop_cols:
            cursor.execute(
                "ALTER TABLE shops ADD COLUMN telethon_daemon_status TEXT"
            )
        if 'telethon_last_activity' not in shop_cols:
            cursor.execute(
                "ALTER TABLE shops ADD COLUMN telethon_last_activity TEXT"
            )
        if 'max_campaigns_daily' not in shop_cols:
            cursor.execute(
                "ALTER TABLE shops ADD COLUMN max_campaigns_daily INTEGER DEFAULT 0"
            )
        if 'current_campaigns_today' not in shop_cols:
            cursor.execute(
                "ALTER TABLE shops ADD COLUMN current_campaigns_today INTEGER DEFAULT 0"
            )

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, shop_id INTEGER)"
        )

        cursor.execute("PRAGMA table_info(categories)")
        cat_cols = [c[1] for c in cursor.fetchall()]
        if "shop_id" not in cat_cols:
            try:
                cursor.execute("ALTER TABLE categories ADD COLUMN shop_id INTEGER DEFAULT 1")
            except sqlite3.OperationalError:
                pass

        cursor.execute(
            """
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
            """
        )

        cursor.execute("PRAGMA table_info(goods)")
        columns = [c[1] for c in cursor.fetchall()]
        updated = False

        if 'additional_description' not in columns:
            cursor.execute("ALTER TABLE goods ADD COLUMN additional_description TEXT DEFAULT ''")
            updated = True
        if 'media_file_id' not in columns:
            cursor.execute("ALTER TABLE goods ADD COLUMN media_file_id TEXT")
            updated = True
        if 'media_type' not in columns:
            cursor.execute("ALTER TABLE goods ADD COLUMN media_type TEXT")
            updated = True
        if 'media_caption' not in columns:
            cursor.execute("ALTER TABLE goods ADD COLUMN media_caption TEXT")
            updated = True
        if 'duration_days' not in columns:
            cursor.execute("ALTER TABLE goods ADD COLUMN duration_days INTEGER DEFAULT NULL")
            updated = True
        if 'manual_delivery' not in columns:
            cursor.execute("ALTER TABLE goods ADD COLUMN manual_delivery INTEGER DEFAULT 0")
            updated = True
        if 'manual_stock' not in columns:
            cursor.execute("ALTER TABLE goods ADD COLUMN manual_stock INTEGER DEFAULT 0")
            updated = True
        if 'category_id' not in columns:
            cursor.execute("ALTER TABLE goods ADD COLUMN category_id INTEGER")
            updated = True
        if 'shop_id' not in columns:
            cursor.execute("ALTER TABLE goods ADD COLUMN shop_id INTEGER DEFAULT 1")
            updated = True

        cursor.execute(
            """
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
            """
        )

        cursor.execute("PRAGMA table_info(campaigns)")
        camp_cols = [c[1] for c in cursor.fetchall()]
        if 'shop_id' not in camp_cols:
            try:
                cursor.execute("ALTER TABLE campaigns ADD COLUMN shop_id INTEGER DEFAULT 1")
                updated = True
            except sqlite3.OperationalError:
                pass

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER,
                username TEXT,
                name_good TEXT,
                amount INTEGER,
                price INTEGER,
                payment_method TEXT,
                timestamp TEXT,
                expires_at TEXT,
                shop_id INTEGER DEFAULT 1
            )
            """
        )

        cursor.execute("PRAGMA table_info(purchases)")
        purch_cols = [c[1] for c in cursor.fetchall()]
        if 'payment_method' not in purch_cols:
            cursor.execute("ALTER TABLE purchases ADD COLUMN payment_method TEXT")
            updated = True
        if 'timestamp' not in purch_cols:
            cursor.execute("ALTER TABLE purchases ADD COLUMN timestamp TEXT")
            updated = True
        if 'expires_at' not in purch_cols:
            cursor.execute("ALTER TABLE purchases ADD COLUMN expires_at TEXT")
            updated = True
        if 'shop_id' not in purch_cols:
            try:
                cursor.execute("ALTER TABLE purchases ADD COLUMN shop_id INTEGER DEFAULT 1")
                updated = True
            except sqlite3.OperationalError:
                pass

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS buyers (
                id INTEGER PRIMARY KEY,
                username TEXT,
                payed INTEGER,
                shop_id INTEGER DEFAULT 1
            )
            """
        )

        cursor.execute("PRAGMA table_info(buyers)")
        buyer_cols = [c[1] for c in cursor.fetchall()]
        if 'shop_id' not in buyer_cols:
            try:
                cursor.execute("ALTER TABLE buyers ADD COLUMN shop_id INTEGER DEFAULT 1")
                updated = True
            except sqlite3.OperationalError:
                pass

        # Tabla que relaciona usuarios con tiendas
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS shop_users (user_id INTEGER PRIMARY KEY, shop_id INTEGER DEFAULT 1)"
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS shop_ratings (
                shop_id INTEGER,
                user_id INTEGER,
                rating INTEGER,
                PRIMARY KEY (shop_id, user_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS discounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                percent INTEGER,
                start_time TEXT,
                end_time TEXT,
                category_id INTEGER,
                shop_id INTEGER
            )
            """
        )

        # Tabla de configuración de descuentos por tienda
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS discount_config (
                id INTEGER PRIMARY KEY,
                discount_enabled INTEGER DEFAULT 1,
                discount_text TEXT DEFAULT '🔥 DESCUENTOS ESPECIALES ACTIVOS 🔥',
                discount_multiplier REAL DEFAULT 1.5,
                show_fake_price INTEGER DEFAULT 1,
                shop_id INTEGER UNIQUE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS store_topics (
                store_id INTEGER,
                group_id TEXT,
                group_name TEXT,
                topic_id INTEGER,
                topic_name TEXT
            )
            """
        )

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS global_config (key TEXT PRIMARY KEY, value TEXT)"
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS unified_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                message TEXT,
                store_id INTEGER
            )
            """
        )


        if updated:
            con.commit()
        con.commit()
    except Exception as e:
        logging.error(f"Error asegurando esquema de base de datos: {e}")
ensure_database_schema()

# -------------------------------------------------
# Utilidad para editar mensajes con o sin multimedia
# -------------------------------------------------
def safe_edit_message(bot, message, text, reply_markup=None, parse_mode=None):
    """Edita de forma segura mensajes de texto o multimedia."""

    content_type = getattr(message, "content_type", "text")

    try:
        if content_type == "text":
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        else:
            bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=message.message_id,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        return True
    except Exception:
        pass

    try:
        if content_type == "text":
            bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=message.message_id,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        else:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        return True
    except Exception as e:
        logging.error(f"Error editando mensaje: {e}")
        try:
            bot.delete_message(message.chat.id, message.message_id)
            bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            logging.error(f"Error enviando nuevo mensaje: {e}")
            return False


def send_long_text(bot, chat_id, text, parse_mode=None):
    """Send a message split in chunks of 4096 characters."""
    for i in range(0, len(text), 4096):
        bot.send_message(chat_id, text[i:i + 4096], parse_mode=parse_mode)


def it_first(chat_id):
    try:
        with open(files.working_log, encoding='utf-8') as f:
            return False
    except Exception as e:
        logging.error(f"Error verificando primer arranque: {e}")
        return True

def log(text):
    time = str(datetime.datetime.now(datetime.UTC))[:22]
    try:
        with open(files.working_log, 'a', encoding='utf-8') as f:
            f.write(time + '    | ' + text + '\n')
    except Exception as e:
        logging.error(f"Error writing log file: {e}")
        with open(files.working_log, 'w', encoding='utf-8') as f:
            f.write(time + '    | ' + text + '\n')

def check_message(message):
    try:
        with shelve.open(files.bot_message_bd) as bd:
            if message in bd:
                return True
            else:
                return False
    except Exception as e:
        logging.error(f"Error comprobando mensaje: {e}")
        return False

def get_adminlist():
    admins_list = [config.admin_id]  # Siempre incluir el admin principal
    cleaned = []
    dirty = False
    try:
        with open(files.admins_list, encoding='utf-8') as f:
            for admin_id in f.readlines():
                try:
                    admin_id = int(admin_id.strip())
                    if admin_id not in admins_list:
                        admins_list.append(admin_id)
                    cleaned.append(f"{admin_id}\n")
                except Exception as e:
                    logging.error(f"Error leyendo id de admin: {e}")
                    dirty = True
        if dirty:
            with open(files.admins_list, 'w', encoding='utf-8') as f:
                f.writelines(cleaned)
    except Exception as e:
        logging.error(f"Error obteniendo lista de admins: {e}")
        pass
    return admins_list

def user_loger(chat_id=0):
    if chat_id != 0:
        try:
            with open(files.users_list, encoding='utf-8') as f:
                if not str(chat_id) in f.read():
                    with open(files.users_list, 'a', encoding='utf-8') as f:
                        f.write(str(chat_id) + '\n')
        except Exception as e:
            logging.error(f"Error registrando usuario: {e}")
            with open(files.users_list, 'w', encoding='utf-8') as f:
                f.write(str(chat_id) + '\n')
        try:
            # Registrar o actualizar la tienda del usuario solo si ya existe
            if user_has_shop(chat_id):
                current = get_user_shop(chat_id)
                set_user_shop(chat_id, current)
        except Exception as e:
            logging.error(f"Error updating user shop: {e}")

    try:
        with open(files.users_list, encoding='utf-8') as f:
            return len(f.readlines())
    except Exception as e:
        logging.error(f"Error contando usuarios: {e}")
        return 0

def get_productcatalog(shop_id=1):
    """Catálogo limpio para una tienda específica"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute("SELECT COUNT(*) FROM goods WHERE shop_id = ?;", (shop_id,))
        product_count = cursor.fetchone()[0]
        
        if product_count == 0:
            return None
        
        # Obtener configuración de descuentos
        discount_config = get_discount_config(shop_id)
        
        # Mensaje del catálogo limpio
        catalog_text = '*Catálogo de productos disponibles:*\n\n'
        
        # Agregar texto de descuento si está habilitado
        if discount_config['enabled']:
            catalog_text += f"*{discount_config['text']}*\n\n"
        
        catalog_text += '*Selecciona un producto para ver detalles y precios*'
        
        return catalog_text
        
    except Exception as e:
        logging.error(f"Error obteniendo catálogo: {e}")
        return None

def get_goods(shop_id=1):
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute("SELECT name FROM goods WHERE shop_id = ?;", (shop_id,))
        goods = []
        for row in cursor.fetchall():
            goods.append(row[0])
        return goods
    except Exception as e:
        logging.error(f"Error obteniendo productos: {e}")
        return []

def list_products_by_category(cat_id=None, shop_id=1):
    """Return product names filtered by category for a shop."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        if cat_id is None:
            cursor.execute(
                "SELECT name FROM goods WHERE shop_id = ?;",
                (shop_id,)
            )
        else:
            cursor.execute(
                "SELECT name FROM goods WHERE shop_id = ? AND category_id = ?;",
                (shop_id, cat_id),
            )
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logging.error(f"Error listando productos por categoría: {e}")
        return []

def list_categories(shop_id=1):
    """Devuelve lista de categorías (id, nombre)."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT id, name FROM categories WHERE shop_id = ? ORDER BY name",
            (shop_id,),
        )
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error listando categorías: {e}")
        return []

def create_category(name, shop_id=1):
    """Crear una categoría y devolver su ID."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "INSERT INTO categories (name, shop_id) VALUES (?, ?)",
            (name, shop_id),
        )
        con.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND shop_id = ?",
            (name, shop_id),
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        logging.error(f"Error creando categoría: {e}")
        return None

def get_category_id(name, shop_id=1):
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT id FROM categories WHERE name = ? AND shop_id = ?",
            (name, shop_id),
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        logging.error(f"Error obteniendo id de categoría: {e}")
        return None

def get_category_name(cat_id, shop_id=1):
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT name FROM categories WHERE id = ? AND shop_id = ?",
            (cat_id, shop_id),
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        logging.error(f"Error obteniendo nombre de categoría: {e}")
        return None

def update_category_name(cat_id, new_name, shop_id=1):
    """Cambiar el nombre de una categoría."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "UPDATE categories SET name = ? WHERE id = ? AND shop_id = ?",
            (new_name, cat_id, shop_id),
        )
        con.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Error actualizando nombre de categoría: {e}")
        return False

def assign_product_category(product, category_id, shop_id=1):
    """Asigna una categoría a un producto."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "UPDATE goods SET category_id = ? WHERE name = ? AND shop_id = ?",
            (category_id, product, shop_id),
        )
        con.commit()
        return True
    except Exception as e:
        logging.error(f"Error asignando categoría: {e}")
        return False

def get_stored(name_good, shop_id=1):
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT stored FROM goods WHERE name = ? AND shop_id = ?;",
            (name_good, shop_id),
        )
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Exception as e:
        logging.error(f"Error obteniendo ruta de almacen: {e}")
        return None

def get_manual_stock(name_good, shop_id=1):
    """Return manual stock for a product."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT manual_stock FROM goods WHERE name = ? AND shop_id = ?",
            (name_good, shop_id),
        )
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception as e:
        logging.error(f"Error obteniendo manual_stock: {e}")
        return 0


def decrement_manual_stock(name_good, quantity, shop_id=1):
    """Decrease manual stock after a purchase."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT manual_stock FROM goods WHERE name = ? AND shop_id = ?",
            (name_good, shop_id),
        )
        row = cursor.fetchone()
        current = int(row[0]) if row and row[0] is not None else 0
        new_val = current - int(quantity)
        if new_val < 0:
            new_val = 0
        cursor.execute(
            "UPDATE goods SET manual_stock = ? WHERE name = ? AND shop_id = ?",
            (new_val, name_good, shop_id),
        )
        con.commit()
    except Exception as e:
        logging.error(f"Error decrementando manual_stock: {e}")


def add_manual_stock(name_good, quantity, shop_id=1):
    """Increase manual stock for a product."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT manual_stock FROM goods WHERE name = ? AND shop_id = ?",
            (name_good, shop_id),
        )
        row = cursor.fetchone()
        current = int(row[0]) if row and row[0] is not None else 0
        new_val = current + int(quantity)
        if new_val < 0:
            new_val = 0
        cursor.execute(
            "UPDATE goods SET manual_stock = ? WHERE name = ? AND shop_id = ?",
            (new_val, name_good, shop_id),
        )
        con.commit()
    except Exception as e:
        logging.error(f"Error incrementando manual_stock: {e}")


def set_manual_stock(name_good, quantity, shop_id=1):
    """Set manual stock to a specific value."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "UPDATE goods SET manual_stock = ? WHERE name = ? AND shop_id = ?",
            (int(quantity), name_good, shop_id),
        )
        con.commit()
    except Exception as e:
        logging.error(f"Error estableciendo manual_stock: {e}")


def amount_of_goods(name_good, shop_id=1):
    if is_manual_delivery(name_good, shop_id):
        return get_manual_stock(name_good, shop_id)
    stored = get_stored(name_good, shop_id)
    if not stored:
        return 0
    try:
        with open(stored, encoding='utf-8') as f:
            lines = f.readlines()
            return len([line for line in lines if line.strip()])
    except Exception as e:
        logging.error(f"Error contando items en almacen: {e}")
        return 0

def get_stock_overview(shop_id=1):
    """Return a list with stock summary lines for all products."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute("SELECT name, price FROM goods WHERE shop_id = ?;", (shop_id,))
        goods = cursor.fetchall()

        overview = []
        for i, (name, price) in enumerate(goods, start=1):
            count = amount_of_goods(name, shop_id)
            overview.append(f"{i}. {name} — {count} unidades (${price} USD)")

        return overview
    except Exception as e:
        logging.error(f"Error generando resumen de stock: {e}")
        return []

def get_minimum(name_good, shop_id=1):
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT minimum FROM goods WHERE name = ? AND shop_id = ?;",
            (name_good, shop_id),
        )
        result = cursor.fetchone()
        if result:
            return result[0]
        return 1
    except Exception as e:
        logging.error(f"Error obteniendo mínimo: {e}")
        return 1

def order_sum(name_good, amount, shop_id=1):
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT price FROM goods WHERE name = ? AND shop_id = ?;",
            (name_good, shop_id),
        )
        result = cursor.fetchone()
        if result:
            price = int(result[0])
            discount = get_active_discount(name_good, shop_id)
            if discount:
                price = int(price * (100 - discount) / 100)
            return price * amount
        return 0
    except Exception as e:
        logging.error(f"Error calculando total del pedido: {e}")
        return 0

def read_my_line(filename, linenumber):
    try:
        with open(filename, encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i == linenumber:
                    return line
        return ""
    except Exception as e:
        logging.error(f"Error leyendo línea {linenumber} de {filename}: {e}")
        return ""

def normal_read_line(filename, linenumber):
    line = read_my_line(filename, linenumber)
    return line.rstrip('\n')

def get_sost(chat_id):
    try:
        with shelve.open(files.sost_bd) as bd:
            return str(chat_id) in bd
    except Exception as e:
        logging.error(f"Error verificando sost para {chat_id}: {e}")
        return False

def check_vklpayments(name):
    try:
        with shelve.open(files.payments_bd) as bd: 
            return bd.get(name, '❌')
    except Exception as e:
        logging.error(f"Error verificando pago habilitado {name}: {e}")
        return '❌'

def get_goodformat(name_good, shop_id=1):
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT format FROM goods WHERE name = ? AND shop_id = ?;",
            (name_good, shop_id),
        )
        result = cursor.fetchone()
        if result:
            return result[0]
        return 'text'
    except Exception as e:
        logging.error(f"Error obteniendo formato: {e}")
        return 'text'

def get_profit(shop_id=1):
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute("SELECT price FROM purchases WHERE shop_id = ?;", (shop_id,))
        price_amount = 0
        for row in cursor.fetchall(): 
            price_amount += int(row[0])
        return price_amount
    except Exception as e:
        logging.error(f"Error calculando ganancias: {e}")
        return 0

def get_amountsbayers(shop_id=1):
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute("SELECT COUNT(*) FROM buyers WHERE shop_id = ?;", (shop_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logging.error(f"Error contando compradores: {e}")
        return 0

def get_amountblock():
    try:
        with open(files.blockusers_list, encoding='utf-8') as f: 
            return len(f.readlines())
    except Exception as e:
        logging.error(f"Error contando usuarios bloqueados: {e}")
        return 0

def new_blockuser(his_id):
    try:
        with open(files.blockusers_list, 'a', encoding='utf-8') as f: 
            f.write(str(his_id) + '\n')
    except Exception as e:
        logging.error(f"Error eliminando id de archivo {file}: {e}")
        pass

def rasl(group, amount, text, shop_id=1):
    good_send = 0
    lose_send = 0
    i = 0
    
    if group == 'all':
        try:
            with open(files.users_list, encoding='utf-8') as f:
                users = f.readlines()
            
            while i < int(amount) and i < len(users):
                chat_id = int(users[i].strip())
                try:
                    bot.send_message(chat_id, text)
                    good_send += 1
                except Exception as e:
                    lose_send += 1
                    logging.error(f"Error enviando mensaje a {chat_id}: {e}")
                    new_blockuser(chat_id)
                i += 1
        except Exception as e:
            logging.error(f"Error enviando mensajes a todos: {e}")
    
    elif group == 'buyers':
        try:
            con = db.get_db_connection()
            cursor = con.cursor()
            cursor.execute(
                "SELECT id FROM buyers WHERE shop_id = ? LIMIT ?;",
                (shop_id, int(amount))
            )
            buyers = cursor.fetchall()
            
            for buyer in buyers:
                chat_id = int(buyer[0])
                try:
                    bot.send_message(chat_id, text)
                    good_send += 1
                except Exception as e:
                    lose_send += 1
                    logging.error(f"Error enviando mensaje a comprador {chat_id}: {e}")
                    new_blockuser(chat_id)
        except Exception as e:
            logging.error(f"Error obteniendo compradores: {e}")

    return f'¡{good_send} usuarios recibieron el mensaje exitosamente!\n{lose_send} usuarios bloquearon el bot y fueron agregados a la lista de usuarios bloqueados'


def _send_media_message(chat_id, text, media):
    """Enviar un mensaje multimedia según el tipo especificado."""
    mtype = media.get('type')
    fid = media.get('file_id')
    caption = media.get('caption') or text

    if mtype == 'photo':
        bot.send_photo(chat_id, fid, caption=caption)
    elif mtype == 'video':
        bot.send_video(chat_id, fid, caption=caption)
    elif mtype == 'document':
        bot.send_document(chat_id, fid, caption=caption)
    elif mtype == 'audio':
        bot.send_audio(chat_id, fid, caption=caption)
    elif mtype == 'animation':
        bot.send_animation(chat_id, fid, caption=caption)
    else:
        bot.send_message(chat_id, text)


def broadcast_message(group, amount, text, media=None, shop_id=1):
    """Enviar un anuncio masivo a usuarios o compradores."""
    good_send = 0
    lose_send = 0
    i = 0

    if group == 'all':
        try:
            con = db.get_db_connection()
            cursor = con.cursor()
            cursor.execute(
                "SELECT user_id FROM shop_users WHERE shop_id = ? LIMIT ?;",
                (shop_id, int(amount)),
            )
            users = cursor.fetchall()

            while i < len(users) and i < int(amount):
                chat_id = int(users[i][0])
                try:
                    if media:
                        _send_media_message(chat_id, text, media)
                    else:
                        bot.send_message(chat_id, text)
                    good_send += 1
                except Exception as e:
                    lose_send += 1
                    logging.error(f"Error sending message to {chat_id}: {e}")
                    new_blockuser(chat_id)
                i += 1
        except Exception as e:
            logging.error(f"Error sending broadcast to all users: {e}")

    elif group == 'buyers':
        try:
            con = db.get_db_connection()
            cursor = con.cursor()
            cursor.execute(
                "SELECT id FROM buyers WHERE shop_id = ? LIMIT ?;",
                (shop_id, int(amount))
            )
            buyers = cursor.fetchall()

            for buyer in buyers:
                chat_id = int(buyer[0])
                try:
                    if media:
                        _send_media_message(chat_id, text, media)
                    else:
                        bot.send_message(chat_id, text)
                    good_send += 1
                except Exception as e:
                    lose_send += 1
                    logging.error(f"Error enviando mensaje a comprador {chat_id}: {e}")
                    new_blockuser(chat_id)
        except Exception as e:
            logging.error(f"Error obteniendo compradores para broadcast: {e}")

    return f'¡{good_send} usuarios recibieron el mensaje exitosamente!\n{lose_send} usuarios bloquearon el bot y fueron agregados a la lista de usuarios bloqueados'

def del_id(file, chat_id):
    try:
        text = ''
        with open(file, encoding='utf-8') as f:
            for line in f.readlines():
                line = line.strip()
                if str(chat_id) != line: 
                    text += line + '\n'
        with open(file, 'w', encoding='utf-8') as f: 
            f.write(text)
    except Exception as e:
        logging.error(f"Error actualizando archivo {file}: {e}")
        pass

def new_admin(his_id):
    try:
        with open(files.admins_list, encoding='utf-8') as f:
            content = f.read()
        if str(his_id) not in content:
            with open(files.admins_list, 'a', encoding='utf-8') as f:
                f.write(str(his_id) + '\n')
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO shops (admin_id, name) VALUES (?, ?)",
            (his_id, f'Shop {his_id}'),
        )
        con.commit()
    except Exception as e:
        logging.error(f"Error agregando nuevo admin: {e}")
        with open(files.admins_list, 'w', encoding='utf-8') as f:
            f.write(str(his_id) + '\n')

def get_shop_id(admin_id):
    """Obtener el ID de tienda asociado a un admin."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT id FROM shops WHERE admin_id = ?", (admin_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("PRAGMA table_info(shops)")
        cols = [c[1] for c in cur.fetchall()]
        if 'campaign_limit' in cols:
            cur.execute(
                "INSERT INTO shops (admin_id, name, campaign_limit) VALUES (?, ?, 0)",
                (admin_id, f'Shop {admin_id}')
            )
        else:
            cur.execute(
                "INSERT INTO shops (admin_id, name) VALUES (?, ?)",
                (admin_id, f'Shop {admin_id}')
            )
        con.commit()
        return cur.lastrowid
    except Exception as e:
        logging.error(f"Error obteniendo shop_id: {e}")
        return None

def list_shops():
    """Listar todas las tiendas registradas."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT id, admin_id, name FROM shops ORDER BY id")
        return cur.fetchall()
    except Exception as e:
        logging.error(f"Error listando tiendas: {e}")
        return []

def create_shop(name, admin_id=None, campaign_limit=0):
    """Crear una nueva tienda y devolver su ID."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute("PRAGMA table_info(shops)")
        cols = [c[1] for c in cur.fetchall()]
        if 'campaign_limit' in cols:
            cur.execute(
                "INSERT INTO shops (admin_id, name, campaign_limit) VALUES (?, ?, ?)",
                (admin_id, name, campaign_limit),
            )
        else:
            cur.execute(
                "INSERT INTO shops (admin_id, name) VALUES (?, ?)",
                (admin_id, name),
            )
        con.commit()
        return cur.lastrowid
    except Exception as e:
        logging.error(f"Error creando tienda: {e}")
        return None

def assign_admin_to_shop(shop_id, admin_id):
    """Asignar un administrador existente a una tienda."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "UPDATE shops SET admin_id = ? WHERE id = ?",
            (admin_id, shop_id)
        )
        con.commit()
        return cur.rowcount > 0
    except Exception as e:
        logging.error(f"Error asignando admin a tienda: {e}")
        return False

def update_shop_name(shop_id, new_name):
    """Cambiar el nombre de una tienda."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "UPDATE shops SET name = ? WHERE id = ?",
            (new_name, shop_id),
        )
        con.commit()
        return cur.rowcount > 0
    except Exception as e:
        logging.error(f"Error actualizando nombre de tienda: {e}")
        return False

def update_shop_info(shop_id, description=None, media_file_id=None, media_type=None,
                     button1_text=None, button1_url=None, button2_text=None, button2_url=None):
    """Actualizar campos de información de una tienda."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        updates = []
        params = []
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if media_file_id is not None:
            updates.append("media_file_id = ?")
            params.append(media_file_id)
        if media_type is not None:
            updates.append("media_type = ?")
            params.append(media_type)
        if button1_text is not None:
            updates.append("button1_text = ?")
            params.append(button1_text)
        if button1_url is not None:
            updates.append("button1_url = ?")
            params.append(button1_url)
        if button2_text is not None:
            updates.append("button2_text = ?")
            params.append(button2_text)
        if button2_url is not None:
            updates.append("button2_url = ?")
            params.append(button2_url)
        if not updates:
            return False
        params.append(shop_id)
        cur.execute(f"UPDATE shops SET {', '.join(updates)} WHERE id = ?", params)
        con.commit()
        return cur.rowcount > 0
    except Exception as e:
        logging.error(f"Error actualizando información de tienda: {e}")
        return False

def get_shop_info(shop_id):
    """Obtener descripción, multimedia y botones de una tienda."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            """
            SELECT description, media_file_id, media_type,
                   button1_text, button1_url, button2_text, button2_url
            FROM shops WHERE id = ?
            """,
            (shop_id,),
        )
        row = cur.fetchone()
        if row:
            return {
                'description': row[0],
                'media_file_id': row[1],
                'media_type': row[2],
                'button1_text': row[3],
                'button1_url': row[4],
                'button2_text': row[5],
                'button2_url': row[6],
            }
        return None
    except Exception as e:
        logging.error(f"Error obteniendo información de tienda: {e}")
        return None

def get_campaign_limit(shop_id):
    """Obtener el límite de campañas para una tienda."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT campaign_limit FROM shops WHERE id = ?", (shop_id,))
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception as e:
        logging.error(f"Error obteniendo campaign_limit: {e}")
        return 0

def set_campaign_limit(shop_id, limit):
    """Actualizar el límite de campañas de una tienda."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "UPDATE shops SET campaign_limit = ? WHERE id = ?",
            (int(limit), shop_id),
        )
        con.commit()
        return cur.rowcount > 0
    except Exception as e:
        logging.error(f"Error estableciendo campaign_limit: {e}")
        return False

# ------------------------------------------------------------------
# Funciones para la tienda seleccionada por cada usuario
# ------------------------------------------------------------------

def set_user_shop(user_id, shop_id):
    """Guardar la tienda elegida por un usuario en la base de datos."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO shop_users (user_id, shop_id) VALUES (?, ?)",
            (int(user_id), int(shop_id)),
        )
        con.commit()
    except Exception as e:
        logging.error(f"Error setting user shop: {e}")


def get_user_shop(user_id):
    """Obtener la tienda seleccionada por un usuario (por defecto 1)."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT shop_id FROM shop_users WHERE user_id = ?",
            (int(user_id),),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 1
    except Exception as e:
        logging.error(f"Error getting user shop: {e}")
        return 1

def user_has_shop(user_id):
    """Return True if the user already selected a shop."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT 1 FROM shop_users WHERE user_id = ?",
            (int(user_id),),
        )
        return cur.fetchone() is not None
    except Exception as e:
        logging.error(f"Error checking user shop: {e}")
        return False

def submit_shop_rating(shop_id, user_id, rating):
    """Insertar o actualizar la calificación de un usuario para una tienda."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO shop_ratings (shop_id, user_id, rating) VALUES (?, ?, ?)",
            (int(shop_id), int(user_id), int(rating)),
        )
        con.commit()
        return True
    except Exception as e:
        logging.error(f"Error submitting shop rating: {e}")
        return False

def get_shop_rating(shop_id):
    """Obtener promedio y cantidad de calificaciones de una tienda."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT AVG(rating), COUNT(*) FROM shop_ratings WHERE shop_id = ?",
            (int(shop_id),),
        )
        row = cur.fetchone()
        if row:
            avg = float(row[0]) if row[0] is not None else 0.0
            return avg, row[1]
        return (0.0, 0)
    except Exception as e:
        logging.error(f"Error getting shop rating: {e}")
        return (0.0, 0)

def get_description(name_good, shop_id=1):
    """Descripción del producto con sistema de descuentos"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT description, price, duration_days FROM goods WHERE name = ? AND shop_id = ?;",
            (name_good, shop_id),
        )
        result = cursor.fetchone()

        if not result:
            return "Producto no encontrado"

        description, price, duration = result
        good_amount = amount_of_goods(name_good, shop_id)
        
        # Obtener configuración de descuentos
        discount_config = get_discount_config(shop_id)
        
        # Construir descripción
        product_description = f"*{name_good}*\n\n"
        product_description += f"📝 *Descripción:*\n{description}\n\n"
        
        active_percent = get_active_discount(name_good, shop_id)

        if active_percent:
            new_price = int(price * (100 - active_percent) / 100)
            orig_str = str(price) + ' USD'
            array = list(orig_str)
            crossed_price = "̶" + "̶".join(array) + "̶"
            product_description += "💰 *Precio:*\n"
            product_description += f"~~{crossed_price}~~\n"
            product_description += f"*${new_price} USD* (-{active_percent}% OFF)\n\n"
        elif discount_config['enabled'] and discount_config['show_fake_price']:
            fake_price = int(price * discount_config['multiplier'])
            fake_price_str = str(fake_price) + ' USD'
            array = list(fake_price_str)
            crossed_price = "̶" + "̶".join(array) + "̶"

            discount_percent = int(((fake_price - price) / fake_price) * 100)

            product_description += f"💰 *Precio:*\n"
            product_description += f"~~{crossed_price}~~ 🔥\n"
            product_description += f"*${price} USD* (-{discount_percent}% OFF)\n\n"
        else:
            product_description += f"💰 *Precio:* ${price} USD\n\n"
        
        product_description += f"📦 *Stock disponible:* {good_amount} unidades\n"
        if duration not in (None, 0):
            product_description += f"⏳ *Duración:* {duration} días\n"
        product_description += f"🛒 *Mínimo de compra:* {get_minimum(name_good, shop_id)} unidades"
        
        return product_description
        
    except Exception as e:
        logging.error(f"Error obteniendo descripción: {e}")
        return "Error obteniendo información del producto"

def get_paypaldata(shop_id=1):
    """Obtener credenciales PayPal asociadas a una tienda."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT client_id, client_secret, sandbox FROM paypal_data WHERE shop_id = ? ORDER BY rowid DESC LIMIT 1;",
            (shop_id,),
        )
        result = cursor.fetchone()
        if result:
            return result[0], result[1], bool(result[2])
        return None
    except Exception as e:
        logging.error(f"Error getting PayPal data: {e}")
        return None

def get_binancedata(shop_id=1):
    """Obtener credenciales Binance asociadas a una tienda."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT api_key, api_secret, merchant_id FROM binance_data WHERE shop_id = ? ORDER BY rowid DESC LIMIT 1;",
            (shop_id,),
        )
        result = cursor.fetchone()
        if result:
            return result[0], result[1], result[2]
        return None
    except Exception as e:
        logging.error(f"Error getting Binance data: {e}")
        return None

def save_paypaldata(client_id, client_secret, sandbox=1, shop_id=1):
    """Guardar o actualizar credenciales PayPal para una tienda."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute("DELETE FROM paypal_data WHERE shop_id = ?", (shop_id,))
        cursor.execute(
            "INSERT INTO paypal_data (client_id, client_secret, sandbox, shop_id) VALUES (?, ?, ?, ?)",
            (client_id, client_secret, int(bool(sandbox)), shop_id),
        )
        con.commit()
        return True
    except Exception as e:
        logging.error(f"Error guardando PayPal data: {e}")
        return False

def save_binancedata(api_key, api_secret, merchant_id, shop_id=1):
    """Guardar o actualizar credenciales Binance para una tienda."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute("DELETE FROM binance_data WHERE shop_id = ?", (shop_id,))
        cursor.execute(
            "INSERT INTO binance_data (api_key, api_secret, merchant_id, shop_id) VALUES (?, ?, ?, ?)",
            (api_key, api_secret, merchant_id, shop_id),
        )
        con.commit()
        return True
    except Exception as e:
        logging.error(f"Error guardando Binance data: {e}")
        return False

def check_paypal_valid(client_id, client_secret, sandbox=True):
    try:
        import paypalrestsdk
        if sandbox:
            paypalrestsdk.configure({
                "mode": "sandbox",
                "client_id": client_id,
                "client_secret": client_secret
            })
        else:
            paypalrestsdk.configure({
                "mode": "live", 
                "client_id": client_id,
                "client_secret": client_secret
            })
        
        # Crear un pago de prueba para verificar credenciales
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [{
                "amount": {"total": "1.00", "currency": "USD"},
                "description": "Test payment"
            }]
        })
        return True
    except Exception as e:
        logging.error(f"Error validando PayPal: {e}")
        return False

def check_binance_valid(api_key, api_secret):
    try:
        from binance.client import Client
        client = Client(api_key, api_secret, testnet=True)
        client.get_account()
        return True
    except Exception as e:
        logging.error(f"Error validando Binance: {e}")
        return False

def payments_checkvkl(shop_id=1):
    """Verificar métodos de pago activos para una tienda."""
    active_payment = []
    
    # Verificar PayPal
    if check_vklpayments('paypal') == '✅' and get_paypaldata(shop_id) != None:
        active_payment.append('paypal')
    elif check_vklpayments('paypal') == '✅' and get_paypaldata(shop_id) == None:
        for admin_id in get_adminlist():
            try:
                bot.send_message(admin_id, '¡Faltan datos de PayPal en la base de datos! Se desactivó automáticamente para recibir pagos.')
            except Exception as e:
                logging.error(f"Error notificando admin {admin_id} por PayPal: {e}")
        try:
            with shelve.open(files.payments_bd) as bd:
                bd['paypal'] = '❌'
        except Exception as e:
            logging.error(f"Error desactivando PayPal: {e}")

    # Verificar Binance
    if check_vklpayments('binance') == '✅' and get_binancedata(shop_id) != None:
        active_payment.append('binance')
    elif check_vklpayments('binance') == '✅' and get_binancedata(shop_id) == None:
        for admin_id in get_adminlist():
            try:
                bot.send_message(admin_id, '¡Faltan datos de Binance en la base de datos! Se desactivó automáticamente para recibir pagos.')
            except Exception as e:
                logging.error(f"Error notificando admin {admin_id} por Binance: {e}")
        try:
            with shelve.open(files.payments_bd) as bd:
                bd['binance'] = '❌'
        except Exception as e:
            logging.error(f"Error desactivando Binance: {e}")

    if len(active_payment) > 0: 
        return active_payment
    else: 
        return None

def generator_pw(n):
    passwd = list('1234567890ABCDEFGHIGKLMNOPQRSTUVYXWZ')
    random.shuffle(passwd)
    pas = ''.join([random.choice(passwd) for x in range(n)])
    return pas

def get_tovar(name_good, shop_id=1):
    try:
        stored = get_stored(name_good, shop_id)
        if not stored:
            return "Producto no encontrado"
            
        with open(stored, encoding='utf-8') as f: 
            lines = f.readlines()
        
        if not lines:
            return "Producto agotado"
            
        # Obtener primera línea y eliminarla
        first_line = lines[0].strip()
        remaining_lines = lines[1:]
        
        with open(stored, 'w', encoding='utf-8') as f: 
            f.writelines(remaining_lines)
        
        return first_line
    except Exception as e:
        logging.error(f"Error obteniendo producto: {e}")
        return "Error obteniendo producto"

def new_buy(his_id, username, name_good, amount, price, shop_id=1):
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "INSERT INTO purchases VALUES(?, ?, ?, ?, ?, ?)",
            (his_id, username, name_good, amount, price, shop_id)
        )
        con.commit()
    except Exception as e:
        logging.error(f"Error registrando compra: {e}")
        pass

def new_buyer(his_id, username, payed, shop_id=1):
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        
        cursor.execute("SELECT payed FROM buyers WHERE id = ? AND shop_id = ?;", (his_id, shop_id))
        result = cursor.fetchone()
        
        if result is None:
            cursor.execute(
                "INSERT INTO buyers VALUES(?, ?, ?, ?)",
                (his_id, username, payed, shop_id)
            )
        else:
            total_payed = int(result[0]) + int(payed)
            cursor.execute(
                "UPDATE buyers SET payed = ? WHERE id = ? AND shop_id = ?;",
                (total_payed, his_id, shop_id)
            )
        
        con.commit()
    except Exception as e:
        logging.error(f"Error actualizando comprador: {e}")
        pass
def new_buy_improved(his_id, username, name_good, amount, price, payment_method="Unknown", payment_id=None, shop_id=1):
    """Versión mejorada de new_buy que incluye método de pago, timestamp y expiración"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()

        # Usar timestamp actual
        from datetime import datetime, timedelta
        current_time = datetime.now().isoformat()

        # Calcular expiración si el producto tiene duración
        duration = get_duration_days(name_good, shop_id)
        expires_at = None
        if duration:
            expires_at = (datetime.now() + timedelta(days=duration)).isoformat()

        cursor.execute(
            """
            INSERT INTO purchases
            (id, username, name_good, amount, price, payment_method, timestamp, expires_at, shop_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (his_id, username, name_good, amount, price, payment_method, current_time, expires_at, shop_id)
        )
        
        # También insertar en tabla de validación si existe
        try:
            cursor.execute("""
                INSERT INTO purchase_validation 
                (user_id, username, product_name, amount, price, payment_method, payment_id, timestamp, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed')
            """, (his_id, username, name_good, amount, price, payment_method, payment_id, current_time))
        except Exception as e:
            logging.error(f"Error insertando en tabla de validación: {e}")
            pass  # Si la tabla no existe, continuar
        
        con.commit()
        return True
    except Exception as e:
        logging.error(f"Error en new_buy_improved: {e}")
        return False

def get_daily_sales(shop_id=1):
    """Obtiene las ventas del día actual"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        
        # Obtener ventas recientes (aproximación por rowid)
        cursor.execute(
            """
            SELECT COUNT(*), SUM(price)
            FROM purchases
            WHERE shop_id = ?
            ORDER BY rowid DESC
            LIMIT 100
            """,
            (shop_id,)
        )
        
        count, total = cursor.fetchone()
        
        cursor.execute(
            """
            SELECT name_good, COUNT(*), SUM(price)
            FROM purchases
            WHERE shop_id = ?
            GROUP BY name_good
            ORDER BY COUNT(*) DESC
            LIMIT 10
            """,
            (shop_id,)
        )
        
        products = cursor.fetchall()
        
        response = "📊 **Estadísticas de Ventas:**\n\n"
        response += f"🛍️ **Transacciones recientes:** {count or 0}\n"
        response += f"💰 **Ingresos totales:** ${total or 0} USD\n\n"
        
        if products:
            response += "📦 **Productos más vendidos:**\n"
            for product, qty, revenue in products:
                response += f"• {product}: {qty} ventas (${revenue} USD)\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error: {e}"

def search_user_purchases(search_term, shop_id=1):
    """Busca compras por ID de usuario o username"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        
        # Si es número, buscar por ID
        if search_term.isdigit():
            cursor.execute(
                """
                SELECT id, username, name_good, amount, price, payment_method, timestamp
                FROM purchases
                WHERE id = ? AND shop_id = ?
                ORDER BY rowid DESC
                """,
                (int(search_term), shop_id),
            )
        else:
            # Si no, buscar por username
            clean_username = search_term.replace('@', '')
            cursor.execute(
                """
                SELECT id, username, name_good, amount, price, payment_method, timestamp
                FROM purchases
                WHERE username LIKE ? AND shop_id = ?
                ORDER BY rowid DESC
                """,
                (f"%{clean_username}%", shop_id),
            )
        
        purchases = cursor.fetchall()
        
        if not purchases:
            return "❌ No se encontraron compras para este usuario"
        
        # Formatear respuesta
        response = f"📋 **Compras encontradas para: {search_term}**\n\n"
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
            except Exception as e:
                logging.error(f"Error formateando fecha {timestamp}: {e}")
                date_str = str(timestamp) if timestamp else "Fecha no disponible"
            
            response += f"🛒 **Compra #{i}**\n"
            response += f"📦 {product} x{amount}\n"
            response += f"💰 ${price} USD\n"
            response += f"💳 {payment_method or 'No especificado'}\n"
            response += f"📅 {date_str}\n"
            response += f"👤 ID: `{user_id}` | @{username}\n"
            response += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        response += f"💎 **Total gastado:** ${total_spent} USD\n"
        response += f"🛍️ **Total compras:** {len(purchases)}"
        
        return response
        
    except Exception as e:
        return f"❌ Error buscando compras: {e}"


def search_products(keyword, limit=10):
    """Search products by keyword.

    The function looks for the keyword in both the product name and
    description using a ``LIKE`` query. It returns a list of tuples with
    ``(shop_id, shop_name, product_name, price)``.

    Example
    -------
    >>> search_products("gift")
    [(1, "Shop 1", "Gift Card", 5)]
    """
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        like = f"%{keyword}%"
        cur.execute(
            """
            SELECT g.shop_id, s.name, g.name, g.price
            FROM goods AS g
            JOIN shops AS s ON g.shop_id = s.id
            WHERE g.name LIKE ? OR g.description LIKE ?
            LIMIT ?
            """,
            (like, like, limit),
        )
        return cur.fetchall()
    except Exception as e:
        logging.error(f"Error searching products: {e}")
        return []


def get_user_purchases(user_id, shop_id=1):
    con = db.get_db_connection()
    cursor = con.cursor()
    cursor.execute(
        "SELECT name_good, amount, price FROM purchases "
        "WHERE id = ? AND shop_id = ? ORDER BY rowid DESC",
        (user_id, shop_id),
    )
    rows = cursor.fetchall()
    if not rows:
        return "❌ No tienes compras registradas."
    response = "📋 **Tus compras:**\n\n"
    total = 0
    for idx, (product, qty, price) in enumerate(rows, 1):
        total += price
        response += (
            f"🛒 **Compra #{idx}**\n"
            f"📦 {product} x{qty}\n"
            f"💰 ${price} USD\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
        )
    response += f"\n💎 **Total gastado:** ${total} USD"
    return response


def get_buyers_summary(shop_id=1):
    """Return purchase summary grouped by buyer."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, MAX(username), SUM(price),
                   GROUP_CONCAT(DISTINCT name_good)
            FROM purchases
            WHERE shop_id = ?
            GROUP BY id
            ORDER BY SUM(price) DESC
            """,
            (shop_id,)
        )
        rows = cur.fetchall()
        lines = []
        for idx, (uid, uname, total, products) in enumerate(rows, 1):
            uname = uname or ''
            prod_list = products or ''
            lines.append(
                f"{idx}. {uid} (@{uname}) - ${total} USD - {prod_list}"
            )
        return lines
    except Exception as e:
        logging.error(f"Error obteniendo resumen de compradores: {e}")
        return []


def get_discount_config(shop_id=1):
    """Obtiene la configuración de descuentos para una tienda"""
    setup_discount_system()
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT discount_enabled, discount_text, discount_multiplier, show_fake_price "
            "FROM discount_config WHERE shop_id = ?;",
            (shop_id,),
        )
        result = cursor.fetchone()
        
        if result:
            return {
                'enabled': bool(result[0]),
                'text': result[1],
                'multiplier': result[2],
                'show_fake_price': bool(result[3])
            }
        else:
            # Configuración por defecto si no existe
            return {
                'enabled': True,
                'text': '🔥 DESCUENTOS ESPECIALES ACTIVOS 🔥',
                'multiplier': 1.5,
                'show_fake_price': True
            }
    except Exception as e:
        logging.error(f"Error obteniendo configuración de descuentos: {e}")
        return {
            'enabled': True,
            'text': '🔥 DESCUENTOS ESPECIALES ACTIVOS 🔥',
            'multiplier': 1.5,
            'show_fake_price': True
        }

def update_discount_config(enabled=None, text=None, multiplier=None, show_fake_price=None, shop_id=1):
    """Actualiza la configuración de descuentos para una tienda"""
    setup_discount_system()
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        
        # Crear tabla si no existe (la migración agrega shop_id si falta)
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

        # Verificar si existe configuración para la tienda
        cursor.execute("SELECT COUNT(*) FROM discount_config WHERE shop_id = ?;", (shop_id,))
        exists = cursor.fetchone()[0] > 0
        
        if not exists:
            # Crear configuración inicial para la tienda
            cursor.execute(
                """
                INSERT INTO discount_config (discount_enabled, discount_text, discount_multiplier, show_fake_price, shop_id)
                VALUES (1, '🔥 DESCUENTOS ESPECIALES ACTIVOS 🔥', 1.5, 1, ?)
                """,
                (shop_id,),
            )
        
        # Actualizar campos especificados
        if enabled is not None:
            cursor.execute(
                "UPDATE discount_config SET discount_enabled = ? WHERE shop_id = ?;",
                (int(enabled), shop_id),
            )
        
        if text is not None:
            cursor.execute(
                "UPDATE discount_config SET discount_text = ? WHERE shop_id = ?;",
                (text, shop_id),
            )
            
        if multiplier is not None:
            cursor.execute(
                "UPDATE discount_config SET discount_multiplier = ? WHERE shop_id = ?;",
                (multiplier, shop_id),
            )
            
        if show_fake_price is not None:
            cursor.execute(
                "UPDATE discount_config SET show_fake_price = ? WHERE shop_id = ?;",
                (int(show_fake_price), shop_id),
            )
        
        con.commit()
        return True
        
    except Exception as e:
        logging.error(f"Error actualizando configuración de descuentos: {e}")
        return False

def setup_discount_system():
    """Configura el sistema de descuentos por primera vez"""
    global _discount_initialized
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        
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
        
        cursor.execute("SELECT COUNT(*) FROM discount_config WHERE shop_id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                INSERT INTO discount_config (discount_enabled, discount_text, discount_multiplier, show_fake_price, shop_id)
                VALUES (1, '🔥 DESCUENTOS ESPECIALES ACTIVOS 🔥', 1.5, 1, 1)
                """
            )
        
        con.commit()
        if not _discount_initialized:
            logging.info("✅ Sistema de descuentos configurado")
            _discount_initialized = True
        return True
        
    except Exception as e:
        logging.error(f"Error configurando sistema de descuentos: {e}")
        return False

def create_discount(percent, start, end=None, category_id=None, shop_id=1):
    """Crear un descuento en la tabla discounts"""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO discounts (percent, start_time, end_time, category_id, shop_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                int(percent),
                start.isoformat() if hasattr(start, "isoformat") else str(start),
                end.isoformat() if hasattr(end, "isoformat") and end else (str(end) if end else None),
                category_id,
                shop_id,
            ),
        )
        con.commit()
        return cur.lastrowid
    except Exception as e:
        logging.error(f"Error creando descuento: {e}")
        return None

def get_active_discount(product_or_cat_id, shop_id=1):
    """Devuelve el porcentaje de descuento activo para un producto o categoría"""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        if isinstance(product_or_cat_id, str):
            cur.execute(
                "SELECT category_id FROM goods WHERE name = ? AND shop_id = ?",
                (product_or_cat_id, shop_id),
            )
            row = cur.fetchone()
            category_id = row[0] if row else None
        else:
            category_id = product_or_cat_id

        now = datetime.datetime.now(datetime.UTC).isoformat()
        cur.execute(
            """
            SELECT percent FROM discounts
            WHERE shop_id = ? AND (category_id IS NULL OR category_id = ?)
              AND start_time <= ? AND (end_time IS NULL OR end_time > ?)
            ORDER BY percent DESC LIMIT 1
            """,
            (shop_id, category_id, now, now),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception as e:
        logging.error(f"Error obteniendo descuento activo: {e}")
        return 0

def update_active_discount_percent(new_percent, shop_id=1):
    """Actualizar el porcentaje de cualquier descuento activo para la tienda"""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        now = datetime.datetime.now(datetime.UTC).isoformat()
        cur.execute(
            """
            UPDATE discounts
            SET percent = ?
            WHERE shop_id = ? AND start_time <= ?
              AND (end_time IS NULL OR end_time > ?)
            """,
            (int(new_percent), shop_id, now, now),
        )
        con.commit()
        return cur.rowcount > 0
    except Exception as e:
        logging.error(f"Error actualizando porcentaje de descuento: {e}")
        return False

# ============================================
# FUNCIONES PARA DESCRIPCIÓN ADICIONAL
# Agregadas automáticamente por el instalador
# ============================================

def get_additional_description(good_name, shop_id=1):
    """Obtiene la descripción adicional de un producto"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute("SELECT additional_description FROM goods WHERE name = ? AND shop_id = ?", (good_name, shop_id))
        result = cursor.fetchone()
        
        if result and result[0]:
            return result[0]
        else:
            return "No hay información adicional disponible para este producto."
    except Exception as e:
        logging.error(f"Error obteniendo descripción adicional: {e}")
        return "Error al cargar información adicional."

def set_additional_description(good_name, additional_description, shop_id=1):
    """Establece la descripción adicional de un producto"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute("UPDATE goods SET additional_description = ? WHERE name = ? AND shop_id = ?",
                      (additional_description, good_name, shop_id))
        con.commit()
        return True
    except Exception as e:
        logging.error(f"Error estableciendo descripción adicional: {e}")
        return False

def get_duration_days(product_name, shop_id=1):
    """Devuelve la duración en días de un producto."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT duration_days FROM goods WHERE name = ? AND shop_id = ?",
            (product_name, shop_id),
        )
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Exception as e:
        logging.error(f"Error obteniendo duración: {e}")
        return None

def set_duration_days(product_name, days, shop_id=1):
    """Establece la duración en días de un producto."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "UPDATE goods SET duration_days = ? WHERE name = ? AND shop_id = ?",
            (days, product_name, shop_id),
        )
        con.commit()
        return True
    except Exception as e:
        logging.error(f"Error estableciendo duración: {e}")
        return False

def is_manual_delivery(product_name, shop_id=1):
    """Indica si un producto requiere entrega manual."""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT manual_delivery FROM goods WHERE name = ? AND shop_id = ?",
            (product_name, shop_id),
        )
        result = cursor.fetchone()
        return bool(result and result[0])
    except Exception as e:
        logging.error(f"Error comprobando entrega manual: {e}")
        return False

def get_manual_delivery_message(username, name):
    """Obtiene el mensaje de entrega manual personalizado."""
    try:
        with shelve.open(files.bot_message_bd) as bd:
            text = bd.get('manual_delivery', 'Gracias por su compra, username')
    except Exception as e:
        logging.error(f"Error retrieving manual delivery message: {e}")
        text = 'Gracias por su compra, username'
    text = text.replace('username', username).replace('name', name)
    return text

def get_product_full_info(good_name, shop_id=1):
    """Obtiene toda la información del producto incluyendo descripción adicional"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            """
            SELECT g.name, g.description, g.additional_description, g.format, g.minimum, g.price,
                   g.duration_days, g.manual_delivery, c.name
            FROM goods g LEFT JOIN categories c ON g.category_id = c.id
            WHERE g.name = ? AND g.shop_id = ?
        """,
            (good_name, shop_id),
        )
        result = cursor.fetchone()

        if result:
            name, description, additional_desc, format, minimum, price, duration_days, manual, category = result
            return {
                'name': name,
                'description': description,
                'additional_description': additional_desc or '',
                'format': format,
                'minimum': minimum,
                'price': price,
                'duration_days': duration_days,
                'manual_delivery': bool(manual),
                'category': category,
            }
        else:
            return None
    except Exception as e:
        logging.error(f"Error obteniendo información completa del producto: {e}")
        return None

def format_product_basic_info(good_name, shop_id=1):
    """Formatea la información básica del producto (sin descripción adicional)"""
    try:
        product_info = get_product_full_info(good_name, shop_id)
        if not product_info:
            return "Producto no encontrado"
        
        amount = amount_of_goods(good_name, shop_id)
        
        format_map = {'text': 'Texto', 'file': 'Archivo'}
        format_display = format_map.get(product_info['format'], product_info['format'])

        info_text = f"""🛍️ **{product_info['name']}**

📝 **Descripción:**
{product_info['description']}"""

        if product_info.get('category'):
            info_text += f"\n🏷️ **Categoría:** {product_info['category']}"

        info_text += f"""

💰 **Precio:** ${product_info['price']} USD
📦 **Cantidad mínima:** {product_info['minimum']}
📋 **Formato:** {format_display}"""

        if product_info.get('manual_delivery'):
            info_text += "\n🚚 **Entrega manual**"
        else:
            info_text += f"\n📊 **Disponibles:** {amount}"

        duration = product_info.get('duration_days')
        if duration not in (None, 0):
            info_text += f"\n⏳ **Duración:** {duration} días"
        
        return info_text
    except Exception as e:
        logging.error(f"Error formateando información básica: {e}")
        return "Error al cargar información del producto"

def format_product_additional_info(good_name, shop_id=1):
    """Formatea la información adicional del producto"""
    try:
        additional_desc = get_additional_description(good_name, shop_id)
        
        info_text = f"""ℹ️ **Información Adicional**

{additional_desc}

━━━━━━━━━━━━━━━━━━━━━━"""
        
        return info_text
    except Exception as e:
        logging.error(f"Error formateando información adicional: {e}")
        return "Error al cargar información adicional"

def has_additional_description(good_name, shop_id=1):
    """Verifica si un producto tiene descripción adicional"""
    try:
        additional_desc = get_additional_description(good_name, shop_id)
        return additional_desc and additional_desc.strip() != "" and additional_desc != "No hay información adicional disponible para este producto."
    except Exception as e:
        logging.error(f"Error verificando descripción adicional: {e}")
        return False

def save_product_media(product_name, file_id, media_type, caption=None, shop_id=1):
    """Guardar información multimedia de un producto"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute("""
            UPDATE goods
            SET media_file_id = ?, media_type = ?, media_caption = ?
            WHERE name = ? AND shop_id = ?
        """, (file_id, media_type, caption, product_name, shop_id))
        con.commit()
        return True
    except Exception as e:
        logging.error(f"Error guardando multimedia: {e}")
        return False

def get_product_media(product_name, shop_id=1):
    """Obtener información multimedia de un producto para una tienda"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            """
            SELECT media_file_id, media_type, media_caption
            FROM goods
            WHERE name = ? AND shop_id = ?
        """,
            (product_name, shop_id),
        )
        result = cursor.fetchone()
        
        if result and result[0]:
            return {
                'file_id': result[0],
                'type': result[1],
                'caption': result[2]
            }
        return None
    except Exception as e:
        logging.error(f"Error obteniendo multimedia: {e}")
        return None

def has_product_media(product_name, shop_id=1):
    """Verificar si un producto tiene multimedia para la tienda indicada"""
    media_info = get_product_media(product_name, shop_id)
    return media_info is not None

def remove_product_media(product_name, shop_id=1):
    """Eliminar multimedia de un producto de una tienda"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            """
            UPDATE goods
            SET media_file_id = NULL, media_type = NULL, media_caption = NULL
            WHERE name = ? AND shop_id = ?
        """,
            (product_name, shop_id),
        )
        con.commit()
        return True
    except Exception as e:
        logging.error(f"Error eliminando multimedia: {e}")
        return False

def get_products_with_media(shop_id=1):
    """Obtener lista de productos que tienen multimedia"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT name, media_type FROM goods WHERE media_file_id IS NOT NULL AND shop_id = ?",
            (shop_id,)
        )
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error obteniendo productos con multimedia: {e}")
        return []

def get_products_without_media(shop_id=1):
    """Obtener lista de productos que NO tienen multimedia"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            "SELECT name FROM goods WHERE media_file_id IS NULL AND shop_id = ?",
            (shop_id,)
        )
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logging.error(f"Error obteniendo productos sin multimedia: {e}")
        return []

def format_product_with_media(product_name, shop_id=1):
    """Formatear información del producto incluyendo multimedia"""
    try:
        con = db.get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            """
            SELECT g.name, g.description, g.price, g.media_file_id, g.media_type, g.media_caption,
                   g.duration_days, g.manual_delivery, c.name
            FROM goods g LEFT JOIN categories c ON g.category_id = c.id
            WHERE g.name = ? AND g.shop_id = ?
        """,
            (product_name, shop_id),
        )
        result = cursor.fetchone()
        
        if not result:
            return None
            
        name, description, price, file_id, media_type, caption, duration, manual, category = result

        discount = get_active_discount(name, shop_id)
        display_price = price
        info = f"🎯 **{name}**\n"
        if discount:
            new_price = int(price * (100 - discount) / 100)
            display_price = new_price
            orig_str = str(price) + ' USD'
            array = list(orig_str)
            crossed = "̶" + "̶".join(array) + "̶"
            info += f"💰 **Precio:** ~~{crossed}~~ ${new_price} USD (-{discount}% OFF)\n"
        else:
            info += f"💰 **Precio:** ${price} USD\n"
        info += f"📝 **Descripción:** {description}\n"
        if category:
            info += f"🏷️ **Categoría:** {category}\n"
        if duration not in (None, 0):
            info += f"⏳ **Duración:** {duration} días\n"

        if manual:
            info += "🚚 **Entrega manual**\n"

        if file_id:
            media_types = {
                'photo': '📸 Imagen',
                'video': '🎥 Video', 
                'document': '📄 Documento',
                'audio': '🎵 Audio',
                'animation': '🎬 GIF'
            }
            media_name = media_types.get(media_type, '📎 Archivo')
            info += f"\n{media_name} disponible"
            
            if caption:
                info += f"\n*{caption}*"
        
        return info
        
    except Exception as e:
        logging.error(f"Error formateando producto: {e}")
        return None

def save_message(message_type, message_text, file_id=None, media_type=None):
    """Guardar mensaje del bot"""
    try:
        with shelve.open(files.bot_message_bd) as bd:
            bd[message_type] = message_text
            if message_type == 'start':
                if file_id:
                    bd['start_media_file_id'] = file_id
                    bd['start_media_type'] = media_type
                else:
                    bd.pop('start_media_file_id', None)
                    bd.pop('start_media_type', None)
        return True
    except Exception as e:
        logging.error(f"Error guardando mensaje: {e}")
        return False


def get_start_media():
    """Obtener multimedia asociada al mensaje de inicio"""
    try:
        with shelve.open(files.bot_message_bd) as bd:
            fid = bd.get('start_media_file_id')
            mtype = bd.get('start_media_type')
        if fid:
            return {'file_id': fid, 'type': mtype}
        return None
    except Exception as e:
        logging.error(f"Error obteniendo multimedia de inicio: {e}")
        return None


def remove_start_media():
    """Eliminar multimedia del mensaje de inicio"""
    try:
        with shelve.open(files.bot_message_bd) as bd:
            bd.pop('start_media_file_id', None)
            bd.pop('start_media_type', None)
        return True
    except Exception as e:
        logging.error(f"Error eliminando multimedia de inicio: {e}")
        return False


def create_product(name, description, format_type, minimum, price, stored,
                   additional_description='', media_file_id=None, media_type=None,
                   media_caption=None, duration_days=None, manual_delivery=0,
                   manual_stock=0, category_id=None, shop_id=1):
    """Crear un producto en la base de datos."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO goods (
                name, description, format, minimum, price, stored,
                additional_description, media_file_id, media_type,
                media_caption, duration_days, manual_delivery,
                manual_stock, category_id, shop_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name, description, format_type, minimum, price, stored,
                additional_description, media_file_id, media_type,
                media_caption, duration_days, manual_delivery,
                manual_stock, category_id, shop_id,
            ),
        )
        con.commit()
        return True
    except Exception as e:
        logging.error(f"Error creando producto: {e}")
        return False


def delete_product(name, shop_id=1):
    """Eliminar un producto de la tienda."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "DELETE FROM goods WHERE name = ? AND shop_id = ?",
            (name, shop_id),
        )
        con.commit()
        return cur.rowcount > 0
    except Exception as e:
        logging.error(f"Error eliminando producto: {e}")
        return False


def update_product_description(name, new_description, shop_id=1):
    """Actualizar la descripción de un producto."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "UPDATE goods SET description = ? WHERE name = ? AND shop_id = ?",
            (new_description, name, shop_id),
        )
        con.commit()
        return cur.rowcount > 0
    except Exception as e:
        logging.error(f"Error actualizando descripción: {e}")
        return False


def update_product_price(name, new_price, shop_id=1):
    """Actualizar el precio de un producto."""
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute(
            "UPDATE goods SET price = ? WHERE name = ? AND shop_id = ?",
            (new_price, name, shop_id),
        )
        con.commit()
        return cur.rowcount > 0
    except Exception as e:
        logging.error(f"Error actualizando precio: {e}")
        return False
