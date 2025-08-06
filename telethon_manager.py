import db


def get_stats(shop_id):
    """Return telethon statistics for a store.

    The stats include whether telethon is active and the number of messages
    sent through the telethon platform for the given shop. Missing tables or
    data result in default values."""
    stats = {"active": False, "sent": 0}
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        try:
            cur.execute(
                "SELECT is_active FROM platform_config WHERE platform='telethon' AND shop_id=?",
                (shop_id,),
            )
            row = cur.fetchone()
            stats["active"] = bool(row[0]) if row else False
        except Exception:
            pass
        try:
            cur.execute(
                "SELECT COUNT(*) FROM send_logs WHERE platform='telethon' AND shop_id=?",
                (shop_id,),
            )
            stats["sent"] = cur.fetchone()[0]
        except Exception:
            pass
    except Exception:
        return stats
    return stats
