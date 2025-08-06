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
