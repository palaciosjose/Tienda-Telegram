import db

try:
    from telethon.sync import TelegramClient
    from telethon.tl.functions.channels import GetForumTopicsRequest
except Exception:  # pragma: no cover - telethon may not be installed in tests
    TelegramClient = None
    GetForumTopicsRequest = None


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


def detect_topics(shop_id, progress_callback=lambda msg: None):
    """Detect topics for a shop using Telethon and store the results.

    The function connects with a :class:`TelegramClient` and iterates over the
    dialogs looking for groups that expose forum topics. Each detected topic is
    saved via :func:`db.save_detected_topics` and a textual summary is returned.
    Progress updates are emitted through ``progress_callback``.
    """

    if TelegramClient is None:
        progress_callback("Telethon no disponible")
        return "Telethon no disponible"

    topics = []
    summary_lines = []

    client = TelegramClient(f"store_{shop_id}", 0, "0")
    try:
        progress_callback("Conectando con Telegram...")
        client.connect()
        dialogs = list(client.iter_dialogs())
        total = len(dialogs) or 1
        for idx, dialog in enumerate(dialogs, 1):
            progress_callback(f"Procesando {idx}/{total}")
            entity = getattr(dialog, "entity", None)
            if entity is None:
                continue

            try:
                result = client(GetForumTopicsRequest(entity, limit=100))
                topic_list = getattr(result, "topics", [])
            except Exception:
                topic_list = []

            if not topic_list:
                continue

            line_topics = []
            for t in topic_list:
                topics.append(
                    {
                        "group_id": str(getattr(entity, "id", "")),
                        "group_name": getattr(dialog, "name", ""),
                        "topic_id": getattr(t, "id", 0),
                        "topic_name": getattr(t, "title", ""),
                    }
                )
                line_topics.append(f"{getattr(t, 'title', '')} ({getattr(t, 'id', 0)})")

            summary_lines.append(
                f"{getattr(dialog, 'name', '')} ({getattr(entity, 'id', '')}): "
                + ", ".join(line_topics)
            )
    finally:
        try:
            client.disconnect()
        except Exception:
            pass

    db.save_detected_topics(shop_id, topics)
    progress_callback("Detección finalizada")
    return "\n".join(summary_lines) if summary_lines else "No se detectaron topics"


def start_auto_detection(shop_id, mode="all", progress_callback=lambda msg: None):
    """Simulate automatic configuration with progress bars."""

    steps = 10
    for step in range(steps + 1):
        bar = "#" * step + "-" * (steps - step)
        progress_callback(f"[{bar}] {int(step / steps * 100)}%")
    return True


def test_send(shop_id):
    """Placeholder to perform a test send using telethon."""
    return True


def restart_daemon(shop_id):
    """Placeholder to restart the telethon daemon for a shop."""
    return True
