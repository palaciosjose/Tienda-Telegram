"""Funciones auxiliares para la integración con :mod:`adminka.py`."""

from .ad_manager import AdvertisingManager
from .statistics import StatisticsManager
import files
import os
import json
import db
from datetime import datetime
import dop
import config
import telethon_manager

# Instancia única usada por los helpers de este módulo
_manager = AdvertisingManager(files.main_db, shop_id=1)

# Reexportamos la instancia por si otros módulos necesitan acceso directo
manager = _manager

def set_shop_id(shop_id):
    """Actualizar la instancia interna con el shop_id indicado."""
    global _manager, manager
    _manager = AdvertisingManager(files.main_db, shop_id=shop_id)
    manager = _manager


def create_campaign_from_admin(data):
    """Crear una campaña mostrando un mensaje apto para la interfaz admin."""

    try:
        data = dict(data)
        data.setdefault('shop_id', _manager.shop_id)
        shop_id = data['shop_id']
        limit = dop.get_campaign_limit(shop_id)
        created_by = data.get('created_by')
        if created_by != config.admin_id and limit and limit > 0:
            current = len(_manager.get_all_campaigns())
            if current >= limit:
                return False, 'Límite de campañas alcanzado'

        campaign_id = _manager.create_campaign(data)
        try:
            stats = telethon_manager.get_stats(shop_id)
            if stats.get("active"):
                telethon_manager.distribute_campaign(shop_id, campaign_id)
        except Exception:
            pass
        return True, f"Campaña creada con ID {campaign_id}"
    except Exception as exc:
        return False, f"Error al crear campaña: {exc}"


def list_campaigns_for_admin():
    """Devolver un resumen de campañas para mostrar en el panel de admin."""

    try:
        campaigns = _manager.get_all_campaigns()
    except Exception as exc:
        return f"Error al obtener campañas: {exc}"

    if not campaigns:
        return "ℹ️ No hay campañas registradas."

    lines = ["📋 *Campañas registradas:*"]
    for camp in campaigns:
        lines.append(f"- {camp['id']}. {camp['name']} ({camp['status']})")
    return "\n".join(lines)


def add_target_group_from_admin(platform, group_id, name=None):
    """Registrar un grupo objetivo y devolver un mensaje para el admin."""

    try:
        ok, msg = _manager.add_target_group(platform, group_id, name)
        return ok, msg
    except Exception as exc:
        return False, f"Error al agregar grupo: {exc}"


def add_bot_group(group_id, title):
    """Registrar un grupo donde el bot está presente."""
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR IGNORE INTO bot_groups (group_id, group_name, added_date)
            VALUES (?, ?, ?)""",
        (str(group_id), title, datetime.now().isoformat()),
    )
    conn.commit()
    return cur.rowcount > 0


def remove_bot_group(group_id):
    """Eliminar un grupo registrado."""
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM bot_groups WHERE group_id = ?", (str(group_id),))
    conn.commit()
    return cur.rowcount > 0


def get_admin_telegram_groups(bot, admin_id):
    """Obtener grupos registrados donde el admin sigue presente."""

    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT group_id, group_name FROM bot_groups")
    rows = cur.fetchall()

    groups = []
    for gid, name in rows:
        try:
            member = bot.get_chat_member(gid, admin_id)
            if getattr(member, "status", "") not in ("left", "kicked"):
                groups.append({"id": gid, "title": name})
        except Exception:
            continue

    return groups


# Las funciones existentes en AdvertisingManager se siguen exponiendo si se
# requieren importarlas directamente desde adminka.py.
