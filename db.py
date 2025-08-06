import sqlite3
import atexit
import files
import config

_connection = None
_connection_path = None

def get_db_connection():
    """Return a cached connection to the main database."""
    global _connection, _connection_path

    if _connection is None or _connection_path != files.main_db:
        if _connection is not None:
            try:
                _connection.close()
            except Exception:
                pass
        _connection = sqlite3.connect(files.main_db, check_same_thread=False)
        _connection_path = files.main_db
    else:
        try:
            _connection.cursor()
        except sqlite3.ProgrammingError:
            _connection = sqlite3.connect(files.main_db, check_same_thread=False)
            _connection_path = files.main_db

    return _connection

def close_connection():
    """Close the cached database connection if it exists."""
    global _connection, _connection_path
    if _connection is not None:
        _connection.close()
        _connection = None
        _connection_path = None

atexit.register(close_connection)


def get_user_role(user_id):
    """Return the role for a given user id."""
    try:
        uid = int(user_id)
    except Exception:
        return "user"

    admins = set()
    try:
        admins.add(int(config.admin_id))
    except Exception:
        pass
    try:
        with open(files.admins_list, encoding="utf-8") as f:
            for line in f:
                try:
                    admins.add(int(line.strip()))
                except ValueError:
                    continue
    except Exception:
        pass

    return "superadmin" if uid in admins else "user"


def get_user_stores(user_id):
    """Return list of stores for the given user.

    Each store is represented as a dictionary with keys:
    id, name, status (bool) and telethon_active (bool).
    """
    stores = []
    try:
        uid = int(user_id)
        con = get_db_connection()
        cur = con.cursor()

        # Determine if shops table has a status column
        cur.execute("PRAGMA table_info(shops)")
        cols = [c[1] for c in cur.fetchall()]
        has_status = "status" in cols

        select_cols = "id, name" + (", status" if has_status else "")
        cur.execute(f"SELECT {select_cols} FROM shops WHERE admin_id = ? ORDER BY id", (uid,))
        rows = cur.fetchall()
        for row in rows:
            sid = row[0]
            name = row[1]
            status = bool(row[2]) if has_status else True

            # Telethon active flag
            cur.execute(
                "SELECT is_active FROM platform_config WHERE platform = 'telethon' AND shop_id = ?",
                (sid,),
            )
            trow = cur.fetchone()
            telethon_active = bool(trow[0]) if trow else False

            stores.append(
                {
                    "id": sid,
                    "name": name,
                    "status": status,
                    "telethon_active": telethon_active,
                }
            )
    except Exception:
        return stores
    return stores


def get_store_stats(store_id):
    """Return basic statistics for a store.

    The function is resilient to missing tables and will return zeros if the
    required data is not available."""
    stats = {"products": 0, "purchases": 0, "revenue": 0}
    try:
        con = get_db_connection()
        cur = con.cursor()

        try:
            cur.execute(
                "SELECT COUNT(*) FROM goods WHERE shop_id = ?",
                (store_id,),
            )
            stats["products"] = cur.fetchone()[0]
        except Exception:
            pass

        try:
            cur.execute(
                "SELECT COUNT(*), COALESCE(SUM(price),0) FROM purchases WHERE shop_id = ?",
                (store_id,),
            )
            row = cur.fetchone()
            stats["purchases"] = row[0]
            stats["revenue"] = row[1]
        except Exception:
            pass
    except Exception:
        return stats

    return stats


def _ensure_global_config_table(cur):
    """Ensure the global_config table exists."""
    cur.execute(
        "CREATE TABLE IF NOT EXISTS global_config (key TEXT PRIMARY KEY, value TEXT)"
    )


def get_global_telethon_status():
    """Return all key/value pairs from the global configuration table."""
    con = get_db_connection()
    cur = con.cursor()
    _ensure_global_config_table(cur)
    cur.execute("SELECT key, value FROM global_config")
    return {k: v for k, v in cur.fetchall()}


def update_global_limit(key, value):
    """Update a limit value in the global configuration table."""
    con = get_db_connection()
    cur = con.cursor()
    _ensure_global_config_table(cur)
    cur.execute(
        "INSERT INTO global_config (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    con.commit()


def save_detected_topics(store_id, topics):
    """Persist detected topics for a given store.

    The topics argument should be an iterable of dictionaries containing the
    keys: group_id, group_name, topic_id and topic_name."""

    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
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
    cur.execute("DELETE FROM store_topics WHERE store_id=?", (store_id,))
    cur.executemany(
        "INSERT INTO store_topics (store_id, group_id, group_name, topic_id, topic_name) VALUES (?, ?, ?, ?, ?)",
        [
            (
                store_id,
                t.get("group_id"),
                t.get("group_name"),
                t.get("topic_id"),
                t.get("topic_name"),
            )
            for t in topics
        ],
    )
    con.commit()
