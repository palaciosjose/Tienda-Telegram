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


def _ensure_store_topics_table(cur):
    """Ensure the store_topics table exists."""
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


def _ensure_unified_logs_table(cur):
    """Ensure the unified_logs table exists."""
    cur.execute(
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


def _ensure_shop_extra_columns(cur):
    """Ensure extended columns exist in shops table."""
    cur.execute("PRAGMA table_info(shops)")
    cols = [c[1] for c in cur.fetchall()]
    if "telethon_enabled" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_enabled INTEGER DEFAULT 0")
    if "telethon_api_id" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_api_id TEXT")
    if "telethon_api_hash" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_api_hash TEXT")
    if "telethon_phone" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_phone TEXT")
    if "telethon_bridge_group" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_bridge_group TEXT")
    if "telethon_daemon_status" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_daemon_status TEXT")
    if "telethon_last_activity" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN telethon_last_activity TEXT")
    if "max_campaigns_daily" not in cols:
        cur.execute("ALTER TABLE shops ADD COLUMN max_campaigns_daily INTEGER DEFAULT 0")
    if "current_campaigns_today" not in cols:
        cur.execute(
            "ALTER TABLE shops ADD COLUMN current_campaigns_today INTEGER DEFAULT 0"
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
    _ensure_store_topics_table(cur)
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


def get_store_topics(store_id):
    """Return stored topics for a given store."""
    con = get_db_connection()
    cur = con.cursor()
    _ensure_store_topics_table(cur)
    cur.execute(
        "SELECT group_id, group_name, topic_id, topic_name FROM store_topics WHERE store_id=?",
        (store_id,),
    )
    rows = cur.fetchall()
    return [
        {
            "group_id": r[0],
            "group_name": r[1],
            "topic_id": r[2],
            "topic_name": r[3],
        }
        for r in rows
    ]


def get_global_metrics():
    """Return aggregated metrics across all shops.

    The metrics include a simple ROI based on total revenue, a ranking of
    shops by revenue and the global Telethon activation status.
    """
    con = get_db_connection()
    cur = con.cursor()

    # Total revenue across all purchases
    try:
        cur.execute("SELECT COALESCE(SUM(price),0) FROM purchases")
        revenue = cur.fetchone()[0] or 0
    except Exception:
        revenue = 0

    # Telethon activation stats
    try:
        cur.execute(
            "SELECT COUNT(*), SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END) "
            "FROM platform_config WHERE platform='telethon'"
        )
        total, active = cur.fetchone()
        total = total or 0
        active = active or 0
    except Exception:
        total = 0
        active = 0

    # Ranking of shops by revenue
    ranking = []
    try:
        cur.execute(
            "SELECT shop_id, COALESCE(SUM(price),0) AS total "
            "FROM purchases GROUP BY shop_id ORDER BY total DESC LIMIT 5"
        )
        rows = cur.fetchall()
        for sid, total_rev in rows:
            try:
                cur.execute("SELECT name FROM shops WHERE id=?", (sid,))
                name_row = cur.fetchone()
                name = name_row[0] if name_row else str(sid)
            except Exception:
                name = str(sid)
            ranking.append({"shop_id": sid, "name": name, "total": total_rev})
    except Exception:
        ranking = []

    return {
        "roi": revenue,
        "revenue": revenue,
        "ranking": ranking,
        "telethon_active": active,
        "telethon_total": total,
    }


def get_alerts(limit=5):
    """Return recent alert-level entries from unified_logs."""
    con = get_db_connection()
    cur = con.cursor()
    _ensure_unified_logs_table(cur)
    try:
        cur.execute(
            "SELECT timestamp, level, message FROM unified_logs "
            "WHERE level IN ('ERROR','WARNING','ALERT') "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
    except Exception:
        rows = []
    return [
        {"timestamp": r[0], "level": r[1], "message": r[2]} for r in rows
    ]


def set_daily_campaign_limit(shop_id, limit):
    """Set the maximum number of campaigns per day for a shop."""
    con = get_db_connection()
    cur = con.cursor()
    _ensure_shop_extra_columns(cur)
    cur.execute(
        "UPDATE shops SET max_campaigns_daily=?, current_campaigns_today=0 WHERE id=?",
        (int(limit), shop_id),
    )
    con.commit()


def get_daily_campaign_counts(shop_id):
    """Return max and current daily campaign counts for a shop."""
    con = get_db_connection()
    cur = con.cursor()
    _ensure_shop_extra_columns(cur)
    cur.execute(
        "SELECT max_campaigns_daily, current_campaigns_today FROM shops WHERE id=?",
        (shop_id,),
    )
    row = cur.fetchone()
    if row:
        return {"max": row[0] or 0, "current": row[1] or 0}
    return {"max": 0, "current": 0}


def register_campaign_send(shop_id):
    """Increment today's campaign count if limit allows."""
    con = get_db_connection()
    cur = con.cursor()
    _ensure_shop_extra_columns(cur)
    counts = get_daily_campaign_counts(shop_id)
    if counts["max"] and counts["current"] >= counts["max"]:
        return False
    cur.execute(
        "UPDATE shops SET current_campaigns_today = current_campaigns_today + 1 WHERE id=?",
        (shop_id,),
    )
    con.commit()
    return True


def reset_daily_campaigns(shop_id=None):
    """Reset the daily campaign counters."""
    con = get_db_connection()
    cur = con.cursor()
    _ensure_shop_extra_columns(cur)
    if shop_id is None:
        cur.execute("UPDATE shops SET current_campaigns_today=0")
    else:
        cur.execute(
            "UPDATE shops SET current_campaigns_today=0 WHERE id=?", (shop_id,)
        )
    con.commit()


def log_event(level, message, store_id=None):
    """Insert an entry into unified_logs."""
    con = get_db_connection()
    cur = con.cursor()
    _ensure_unified_logs_table(cur)
    cur.execute(
        "INSERT INTO unified_logs (level, message, store_id) VALUES (?, ?, ?)",
        (level, message, store_id),
    )
    con.commit()


def get_unified_logs(limit=100, store_id=None):
    """Retrieve logs from unified_logs table."""
    con = get_db_connection()
    cur = con.cursor()
    _ensure_unified_logs_table(cur)
    if store_id is None:
        cur.execute(
            "SELECT id, timestamp, level, message, store_id FROM unified_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
    else:
        cur.execute(
            "SELECT id, timestamp, level, message, store_id FROM unified_logs WHERE store_id=? ORDER BY id DESC LIMIT ?",
            (store_id, limit),
        )
    rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "timestamp": r[1],
            "level": r[2],
            "message": r[3],
            "store_id": r[4],
        }
        for r in rows
    ]

