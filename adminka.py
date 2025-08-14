import telebot, sqlite3, shelve, os, json, re, datetime
import config, dop, files
import db
import telethon_config
import telethon_manager
from utils.ascii_chart import sparkline
from business_intelligence import generate_bi_report
from utils.professional_box import render_box
from advertising_system.admin_integration import (
    manager as advertising,
    set_shop_id,
    create_campaign_from_admin,
    list_campaigns_for_admin,
    add_target_group_from_admin,
    get_admin_telegram_groups,
)
from bot_instance import bot
from advertising_system.scheduler import CampaignScheduler
from navigation import nav_system
from utils.message_chunker import send_long_message

import logging

logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def set_state(chat_id, state, prev="main"):
    """Store user state and previous menu"""
    with shelve.open(files.sost_bd) as bd:
        bd[str(chat_id)] = state
        bd[f"{chat_id}_prev"] = prev


def clear_state(chat_id):
    """Remove stored state"""
    with shelve.open(files.sost_bd) as bd:
        if str(chat_id) in bd:
            del bd[str(chat_id)]
        key = f"{chat_id}_prev"
        if key in bd:
            del bd[key]


def cancel_and_reset(chat_id):
    """Clear user state and notify cancellation"""
    clear_state(chat_id)
    send_long_message(bot, chat_id, "❌ Operación cancelada.")


def get_prev(chat_id):
    with shelve.open(files.sost_bd) as bd:
        return bd.get(f"{chat_id}_prev", "main")


def route_cancel(chat_id, prev):
    if prev == "marketing":
        show_marketing_menu(chat_id)
    elif prev == "discount":
        show_discount_menu(chat_id)
    elif prev == "product":
        show_product_menu(chat_id)
    elif prev == "other":
        admin_otros(chat_id, 0)
    else:
        show_main_admin_menu(chat_id)


# ---------------------------------------------------------------------------
# Main admin menus
# ---------------------------------------------------------------------------


def show_main_admin_menu(chat_id):
    """Mostrar el menú principal de administración usando navegación unificada."""
    quick_actions = []
    if chat_id == config.admin_id:
        quick_actions.append(("💬 Respuestas", "ad_respuestas"))
    quick_actions.extend(
        [
            ("📦 Surtido", "ad_surtido"),
            ("➕ Producto", "ad_producto"),
            ("💰 Pagos", "ad_pagos"),
            ("📊 Stats", "ad_stats"),
            ("📣 Difusión", "ad_difusion"),
            ("👥 Clientes", "ad_resumen"),
            ("📢 Marketing", "ad_marketing"),
            ("🏷️ Categorías", "ad_categorias"),
            ("💸 Descuentos", "ad_descuentos"),
            ("⚙️ Otros", "ad_otros"),
        ]
    )
    key = nav_system.create_universal_navigation(chat_id, "admin_main", quick_actions)
    send_long_message(
        bot,
        chat_id,
        "¡Has ingresado al panel de administración del bot!\nPara salir, presiona /start",
        markup=key,
    )


def session_expired(chat_id):
    """Informar al usuario que la sesión expiró y volver al menú principal"""
    send_long_message(bot, chat_id, "❌ La sesión anterior se perdió.")
    with shelve.open(files.sost_bd) as bd:
        if str(chat_id) in bd:
            del bd[str(chat_id)]
    show_main_admin_menu(chat_id)


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------


def show_store_dashboard_unified(chat_id, store_id, store_name):
    """Mostrar panel unificado de la tienda con estadísticas básicas."""
    stats = db.get_store_stats(store_id)
    tele_stats = telethon_manager.get_stats(store_id)
    sales_ts = db.get_sales_timeseries(store_id)
    camp_ts = db.get_campaign_timeseries(store_id)
    topics = db.get_store_topics(store_id)

    campaign_count = 0
    daemon_status = "-"
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM campaigns WHERE shop_id=?", (store_id,))
            campaign_count = cur.fetchone()[0]
        except Exception:
            campaign_count = 0
        try:
            cur.execute(
                "SELECT telethon_daemon_status FROM shops WHERE id=?",
                (store_id,),
            )
            row = cur.fetchone()
            daemon_status = row[0] if row else "-"
        except Exception:
            daemon_status = "-"
    except Exception:
        pass

    lines = [f"📊 *Dashboard de {store_name}*"]
    lines.append(f"📦 Productos: {stats.get('products', 0)}")
    lines.append(f"🛒 Ventas totales: {stats.get('purchases', 0)}")
    if "revenue" in stats:
        lines.append(f"💵 Ingresos: ${stats.get('revenue', 0)}")
    if sales_ts:
        vals = [s['total'] for s in sales_ts]
        delta = vals[-1] - (vals[-2] if len(vals) > 1 else 0)
        lines.append(f"💰 Ventas 7d: {sparkline(vals)} ({delta:+})")
    if camp_ts:
        vals = [c['count'] for c in camp_ts]
        delta = vals[-1] - (vals[-2] if len(vals) > 1 else 0)
        lines.append(f"📈 Envíos 7d: {sparkline(vals)} ({delta:+})")
    lines.append(f"🗂️ Topics: {len(topics)}")
    lines.append(f"📣 Campañas: {campaign_count}")

    tele_state = "Activo" if tele_stats.get("active") else "Inactivo"
    lines.append(f"🤖 Telethon: {tele_state}")
    sent = tele_stats.get("sent", 0)
    if sent:
        lines.append(f"✉️ Envíos Telethon: {sent}")
    lines.append(f"🔁 Daemon: {daemon_status}")

    message = "\n".join(lines)

    quick_actions = [
        ("🏪 Tienda", "dash_shop_info"),
        ("📦 Surtido", "ad_surtido"),
        ("➕ Producto", "ad_producto"),
        ("💰 Pagos", "ad_pagos"),
        ("📊 Stats", "ad_stats"),
        ("📣 Difusión", "ad_difusion"),
        ("👥 Clientes", "ad_resumen"),
        ("📢 Marketing", "ad_marketing"),
        ("🤖 Telethon", "dash_telethon"),
        ("🧾 Reportes", "dash_reports"),
        ("⚙️ Config", "dash_config"),
        ("🏷️ Categorías", "ad_categorias"),
        ("💸 Descuentos", "ad_descuentos"),
        ("⚙️ Otros", "ad_otros"),
        ("⬅️ Cambiar", "dash_change_store"),
    ]

    key = nav_system.create_universal_navigation(
        chat_id, f"store_dashboard_{store_id}", quick_actions
    )
    send_long_message(
        bot, chat_id, message, markup=key, parse_mode="Markdown"
    )


def show_marketing_unified(chat_id, store_id):
    """Mostrar un panel compacto con campañas, programación y Telethon."""
    try:
        campaigns = advertising.get_all_campaigns()
    except Exception:
        campaigns = []
    limit = dop.get_campaign_limit(store_id)

    active = [c for c in campaigns if c.get("status") == "active"]
    scheduler = CampaignScheduler(files.main_db, shop_id=store_id)
    try:
        pending = scheduler.get_pending_sends()
    except Exception:
        pending = []

    tele_stats = telethon_manager.get_stats(store_id)
    tele_state = "Activo" if tele_stats.get("active") else "Inactivo"

    lines = ["📣 *Panel de Marketing*"]
    if limit:
        lines.append(f"⚡ {len(active)}/{limit}")
    else:
        lines.append(f"⚡ {len(active)}")
    lines.append("")
    lines.append("*Campañas activas:*")
    if active:
        for camp in active:
            lines.append(f"- {camp.get('id')}. {camp.get('name', '')}")
    else:
        lines.append("- Ninguna")
    lines.append("")
    lines.append("*Programación:*")
    if pending:
        for p in pending:
            name = p[8] if len(p) > 8 else f"ID {p[1] if len(p)>1 else '?'}"
            lines.append(f"- {name}")
    else:
        lines.append("- Ninguna")
    lines.append("")
    lines.append("*Telethon:*")
    lines.append(f"Estado: {tele_state}")

    message = "\n".join(lines)

    quick_actions = [
        ("➕ Nueva", "quick_new_campaign"),
        ("🤖 Telethon", "quick_telethon"),
        ("📊 Stats", "quick_stats"),
    ]
    key = nav_system.create_universal_navigation(
        chat_id, f"marketing_{store_id}", quick_actions
    )
    send_long_message(bot, chat_id, message, markup=key, parse_mode="Markdown")


def quick_new_campaign(chat_id, store_id):
    key = nav_system.create_universal_navigation(chat_id, "new_campaign")
    send_long_message(
        bot,
        chat_id,
        "📝 *Nombre de la campaña*\n\nEnvía el nombre para la nueva campaña:",
        markup=key,
        parse_mode="Markdown",
    )
    set_state(chat_id, 160, prev="marketing")


def quick_telethon(chat_id, store_id):
    stats = telethon_manager.get_stats(store_id)
    msg = "Activo" if stats.get("active") else "Inactivo"
    send_long_message(bot, chat_id, f"🤖 Telethon: {msg}")


def quick_stats(chat_id, store_id):
    text = list_campaigns_for_admin()
    send_long_message(bot, chat_id, text, parse_mode="Markdown")


nav_system.register("quick_new_campaign", quick_new_campaign)
nav_system.register("quick_telethon", quick_telethon)
nav_system.register("quick_stats", quick_stats)


def show_discount_menu(chat_id):
    """Mostrar menú de configuración de descuentos con navegación unificada."""
    shop_id = dop.get_shop_id(chat_id)
    config_dis = dop.get_discount_config(shop_id)

    status = "Activado ✅" if config_dis["enabled"] else "Desactivado ❌"
    show_fake = "Sí" if config_dis["show_fake_price"] else "No"

    toggle = "🚫 Desactivar" if config_dis["enabled"] else "✅ Activar"
    toggle_fake = "🖍️ Tachado"  # toggle show_fake_price

    quick_actions = [
        (toggle, "discount_toggle"),
        ("✏️ Texto", "discount_text"),
        ("📉 %", "discount_percent"),
        (toggle_fake, "discount_fake"),
        ("➕ Nuevo", "discount_new"),
        ("👀 Vista", "discount_preview"),
    ]

    key = nav_system.create_universal_navigation(
        chat_id, "discount_menu", quick_actions
    )

    message = (
        f"💸 *Configuración de Descuentos*\n\n"
        f"Estado: {status}\n"
        f"Texto: {config_dis['text']}\n"
        f"Multiplicador: x{config_dis['multiplier']}\n"
        f"Mostrar precios tachados: {show_fake}"
    )

    send_long_message(bot, chat_id, message, markup=key, parse_mode="Markdown")


def show_product_menu(chat_id):
    """Mostrar el nuevo dashboard unificado para gestión de productos."""
    shop_id = dop.get_shop_id(chat_id)
    try:
        con = db.get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT name FROM shops WHERE id = ?", (shop_id,))
        row = cur.fetchone()
        name = row[0] if row else str(shop_id)
    except Exception:
        name = str(shop_id)
    show_store_dashboard_unified(chat_id, shop_id, name)


def show_marketing_menu(chat_id):
    shop_id = dop.get_shop_id(chat_id)
    show_marketing_unified(chat_id, shop_id)


def show_superadmin_dashboard(chat_id, user_id):
    """Mostrar panel del super admin con métricas globales de tiendas."""
    if user_id != config.admin_id:
        send_long_message(bot, chat_id, "❌ Acceso restringido.")
        return

    con = db.get_db_connection()
    cur = con.cursor()
    try:
        cur.execute(
            "SELECT id, name, COALESCE(telethon_daemon_status, '-') FROM shops ORDER BY id"
        )
        shops = cur.fetchall()
    except Exception:
        shops = []

    total_sales = total_revenue = total_topics = total_campaigns = 0
    active_daemons = 0

    for sid, name, daemon_status in shops:
        try:
            cur.execute(
                "SELECT is_active FROM platform_config WHERE platform='telethon' AND shop_id=?",
                (sid,),
            )
            row = cur.fetchone()
            tele_active = bool(row[0]) if row else False
        except Exception:
            tele_active = False
        tele_txt = "✅" if tele_active else "❌"

        try:
            cur.execute(
                "SELECT COUNT(*), COALESCE(SUM(price),0) FROM purchases WHERE shop_id=?",
                (sid,),
            )
            count, total = cur.fetchone()
        except Exception:
            count, total = 0, 0

        try:
            cur.execute(
                "SELECT COUNT(*) FROM store_topics WHERE store_id=?",
                (sid,),
            )
            topics = cur.fetchone()[0]
        except Exception:
            topics = 0

        try:
            cur.execute("SELECT COUNT(*) FROM campaigns WHERE shop_id=?", (sid,))
            campaigns = cur.fetchone()[0]
        except Exception:
            campaigns = 0

        total_sales += count
        total_revenue += total or 0
        total_topics += topics
        total_campaigns += campaigns
        if daemon_status not in ("-", None, "stopped"):
            active_daemons += 1


    global_campaign_limit = int(os.getenv("GLOBAL_CAMPAIGN_LIMIT", 0))
    global_topic_limit = int(os.getenv("GLOBAL_TOPIC_LIMIT", 0))
    summary_box = render_box(
        [
            f"Ventas: {total_sales}/{total_revenue}",
            f"Campañas: {total_campaigns}",
            f"Topics: {total_topics}",
            f"Daemons activos: {active_daemons}/{len(shops)}",
            f"Límite campañas/día: {global_campaign_limit}",
            f"Topics máximos: {global_topic_limit}",
        ],
        title="Resumen Global",
    )

    message_lines = [summary_box, "", "📊 *Resumen de tiendas*"]

    quick_actions = []
    for sid, name, _ in shops:
        quick_actions.append((f"📊 {name}", f"view_store_{sid}"))
        quick_actions.append(("⚙️ Administrar", f"admin_store_{sid}"))

    quick_actions.extend(
        [
            ("🏪 Tiendas", "admin_list_shops"),
            ("➕ Crear Tienda", "admin_create_shop"),
            ("🤖 Telethon Global", "global_telethon_config"),
            ("🔁 Reiniciar todos", "global_restart_daemons"),
            ("📊 BI Reporte", "admin_bi_report"),
        ]
    )

    key = nav_system.create_universal_navigation(
        chat_id, "superadmin_dashboard", quick_actions
    )
    send_long_message(
        bot, chat_id, "\n".join(message_lines), markup=key, parse_mode="Markdown"
    )


def _superadmin_dashboard_nav(chat_id, user_id):
    show_superadmin_dashboard(chat_id, user_id)


nav_system.register("superadmin_dashboard", _superadmin_dashboard_nav)
nav_system.register("select_store_main", _superadmin_dashboard_nav)


def admin_list_shops(chat_id, user_id):
    """Mostrar listado detallado de tiendas para el superadmin."""
    if user_id != config.admin_id:
        key = nav_system.create_universal_navigation(
            chat_id, "admin_list_shops_denied"
        )
        send_long_message(bot, chat_id, "❌ Acceso restringido.", markup=key)
        return

    shops = dop.list_shops()
    if shops:
        lines = [f"{sid}. {name} (admin {aid})" for sid, aid, name in shops]
    else:
        lines = ["No hay tiendas registradas"]

    box = render_box(lines, title="Tiendas registradas")
    key = nav_system.create_universal_navigation(chat_id, "admin_list_shops")
    send_long_message(bot, chat_id, box, markup=key, parse_mode="Markdown")


def admin_create_shop(chat_id, user_id):
    """Iniciar asistente para crear una nueva tienda."""
    if user_id != config.admin_id:
        key = nav_system.create_universal_navigation(
            chat_id, "admin_create_shop_denied"
        )
        send_long_message(bot, chat_id, "❌ Acceso restringido.", markup=key)
        return

    key = nav_system.create_universal_navigation(chat_id, "admin_create_shop_name")
    send_long_message(
        bot,
        chat_id,
        "🆕 *Creación de tienda*\n\nIngresa el nombre de la nueva tienda:",
        markup=key,
        parse_mode="Markdown",
    )
    set_state(chat_id, 900, "main")


def admin_bi_report(chat_id, user_id):
    """Enviar reporte de Business Intelligence al SuperAdmin."""
    if db.get_user_role(user_id) != "superadmin":
        key = nav_system.create_universal_navigation(
            chat_id, "admin_bi_report_denied"
        )
        send_long_message(
            bot,
            chat_id,
            "❌ Solo SuperAdmin.",
            markup=key,
        )
        db.log_event("WARNING", f"user {user_id} denied bi_report")
        return

    send_long_message(bot, chat_id, "⏳ Generando reporte...")
    report = generate_bi_report()
    key = nav_system.create_universal_navigation(chat_id, "admin_bi_report")
    send_long_message(bot, chat_id, report, markup=key, parse_mode="Markdown")
    db.log_event("INFO", f"user {user_id} viewed bi_report")


# Compatibilidad retroactiva
show_bi_report = admin_bi_report


def _admin_list_shops_nav(chat_id, user_id):
    admin_list_shops(chat_id, user_id)


def _admin_create_shop_nav(chat_id, user_id):
    admin_create_shop(chat_id, user_id)


nav_system.register("admin_list_shops", _admin_list_shops_nav)
nav_system.register("admin_create_shop", _admin_create_shop_nav)


def _global_telethon_config(chat_id, user_id):
    telethon_config.global_telethon_config("admin_telethon_config", chat_id, user_id)


def _global_restart_daemons(chat_id, user_id):
    telethon_config.global_telethon_config("global_restart_daemons", chat_id, user_id)


nav_system.register("global_telethon_config", _global_telethon_config)
nav_system.register("global_restart_daemons", _global_restart_daemons)


def _admin_bi_report_nav(chat_id, user_id):
    show_bi_report(chat_id, user_id)


nav_system.register("admin_bi_report", _admin_bi_report_nav)


def route_superadmin_callback(callback_data, chat_id, user_id):
    """Dispatch superadmin dashboard callbacks to their handlers."""
    if callback_data in (
        "admin_telethon_config",
        "global_telethon_config",
        "global_restart_daemons",
    ):
        telethon_config.global_telethon_config(callback_data, chat_id, user_id)
        return

    nav_system.handle(callback_data, chat_id, user_id)


# ---------------------------------------------------------------------------
# Administrative section handlers
# ---------------------------------------------------------------------------


def admin_respuestas(chat_id, store_id):
    key = nav_system.create_universal_navigation(chat_id, "admin_respuestas")
    send_long_message(
        bot, chat_id, "💬 Gestión de respuestas no disponible.", markup=key
    )


def admin_surtido(chat_id, store_id):
    show_product_menu(chat_id)


def manage_products(chat_id, store_id):
    """Listado simple de productos disponibles en la tienda."""
    goods = dop.get_goods(store_id)
    lines = ["📦 *Productos disponibles:*"]
    if goods:
        lines.extend(f"- {g}" for g in goods)
    else:
        lines.append("- Ninguno")
    message = "\n".join(lines)
    key = nav_system.create_universal_navigation(chat_id, "manage_products")
    send_long_message(bot, chat_id, message, markup=key, parse_mode="Markdown")


def config_payments(chat_id, store_id):
    """Mostrar estado de configuración de los métodos de pago."""
    paypal = "Configurado ✅" if dop.get_paypaldata(store_id) else "No configurado ❌"
    binance = "Configurado ✅" if dop.get_binancedata(store_id) else "No configurado ❌"
    message = (
        "💰 *Configuración de Pagos*\n\n"
        f"PayPal: {paypal}\n"
        f"Binance Pay: {binance}"
    )
    key = nav_system.create_universal_navigation(chat_id, "config_payments")
    send_long_message(bot, chat_id, message, markup=key, parse_mode="Markdown")


def view_stats(chat_id, store_id):
    """Mostrar estadísticas de ventas para la tienda."""
    try:
        stats = dop.get_daily_sales(store_id)
    except Exception:
        stats = f"Stats: {dop.get_profit(store_id)} USD total"
    key = nav_system.create_universal_navigation(chat_id, "view_stats")
    send_long_message(bot, chat_id, stats, markup=key, parse_mode="Markdown")


def admin_difusion(chat_id, store_id):
    key = nav_system.create_universal_navigation(chat_id, "admin_difusion")
    send_long_message(bot, chat_id, "📣 Difusión no disponible.", markup=key)


def admin_resumen(chat_id, store_id):
    key = nav_system.create_universal_navigation(chat_id, "admin_resumen")
    send_long_message(bot, chat_id, "👥 Clientes no disponible.", markup=key)


def admin_marketing(chat_id, store_id):
    show_marketing_menu(chat_id)


def admin_categorias(chat_id, store_id):
    key = nav_system.create_universal_navigation(chat_id, "admin_categorias")
    send_long_message(bot, chat_id, "🏷️ Categorías no disponible.", markup=key)


def admin_descuentos(chat_id, store_id):
    show_discount_menu(chat_id)


def admin_otros(chat_id, store_id):
    key = nav_system.create_universal_navigation(chat_id, "admin_otros")
    send_long_message(bot, chat_id, "⚙️ Opciones adicionales no disponibles.", markup=key)


nav_system.register("ad_respuestas", admin_respuestas)
nav_system.register("ad_surtido", admin_surtido)
nav_system.register("ad_producto", manage_products)
nav_system.register("ad_pagos", config_payments)
nav_system.register("ad_stats", view_stats)
nav_system.register("ad_difusion", admin_difusion)
nav_system.register("ad_resumen", admin_resumen)
nav_system.register("ad_marketing", admin_marketing)
nav_system.register("ad_categorias", admin_categorias)
nav_system.register("ad_descuentos", admin_descuentos)
nav_system.register("ad_otros", admin_otros)


# Wrapper used in tests to dispatch callbacks without the legacy system
def ad_inline(callback_data, chat_id, message_id):
    nav_system.handle(callback_data, chat_id, dop.get_shop_id(chat_id))


# ---------------------------------------------------------------------------
# Product campaign creation
# ---------------------------------------------------------------------------


def finalize_product_campaign(chat_id, shop_id, product):
    """Crear campaña de producto usando la información almacenada."""
    info = dop.get_product_full_info(product, shop_id)
    if not info:
        bot.send_message(chat_id, "❌ Producto no encontrado.")
        return

    text = info["description"] or ""
    if info.get("additional_description"):
        extra = info["additional_description"]
        if extra:
            text += ("\n" if text else "") + extra

    media = dop.get_product_media(product, shop_id)
    media_file_id = media["file_id"] if media else None
    media_type = media["type"] if media else None

    data = {
        "name": f"Producto {product}",
        "message_text": text,
        "media_file_id": media_file_id,
        "media_type": media_type,
        "button1_text": "Ver producto",
        "button1_url": dop.get_product_link(product, shop_id),
        "created_by": chat_id,
    }
    ok, msg = create_campaign_from_admin(data)
    bot.send_message(chat_id, ("✅ " if ok else "❌ ") + msg)
    with shelve.open(files.sost_bd) as bd:
        if str(chat_id) in bd:
            del bd[str(chat_id)]
    show_marketing_menu(chat_id)


# ---------------------------------------------------------------------------
# Legacy interface compatibility (minimal)
# ---------------------------------------------------------------------------


def in_adminka(chat_id, message_text, username, name_user):
    """Minimal handler preserving legacy entry points for tests."""
    if chat_id not in dop.get_adminlist():
        return
    shop_id = dop.get_shop_id(chat_id)
    set_shop_id(shop_id)
    if message_text == "🛒 Campaña de producto":
        goods = dop.get_goods(shop_id)
        if not goods:
            send_long_message(bot, chat_id, "No hay productos disponibles.")
            return
        lines = ["Seleccione el producto para la campaña:"]
        lines.extend(f"- {g}" for g in goods)
        send_long_message(bot, chat_id, "\n".join(lines))
        set_state(chat_id, 190, "marketing")
    else:
        show_main_admin_menu(chat_id)


def text_analytics(message_text, chat_id):
    shop_id = dop.get_shop_id(chat_id)
    normalized = message_text.strip().lower()
    if normalized in (
        "cancelar",
        "volver al menú principal",
        "volver al menu principal",
        "/adm",
    ):
        cancel_and_reset(chat_id)
        show_main_admin_menu(chat_id)
        return

    if dop.get_sost(chat_id):
        with shelve.open(files.sost_bd) as bd:
            sost_num = bd.get(str(chat_id))

        if sost_num == 190:
            goods = dop.get_goods(shop_id)
            if message_text not in goods:
                send_long_message(bot, chat_id, "Selección inválida. Intente nuevamente.")
                return
            finalize_product_campaign(chat_id, shop_id, message_text)
        elif sost_num == 900:
            # Recibir nombre de tienda
            with shelve.open(files.sost_bd) as bd:
                bd[f"{chat_id}_new_shop_name"] = message_text.strip()
            key = nav_system.create_universal_navigation(
                chat_id, "admin_create_shop_admin"
            )
            send_long_message(
                bot,
                chat_id,
                "👤 Ingresa el ID del administrador de la tienda:",
                markup=key,
            )
            set_state(chat_id, 901, "main")
        elif sost_num == 901:
            # Recibir ID del administrador y crear tienda
            try:
                admin_id = int(message_text.strip())
            except ValueError:
                send_long_message(bot, chat_id, "❌ ID inválido. Intenta nuevamente:")
                return
            with shelve.open(files.sost_bd) as bd:
                name = bd.pop(f"{chat_id}_new_shop_name", "Tienda")
                if str(chat_id) in bd:
                    del bd[str(chat_id)]
            send_long_message(bot, chat_id, "⏳ Creando tienda...")
            shop_id_new = dop.create_shop(name, admin_id=admin_id)
            send_long_message(
                bot,
                chat_id,
                f"✅ Tienda '{name}' creada (ID: {shop_id_new}).",
            )
            show_superadmin_dashboard(chat_id, chat_id)
        else:
            clear_state(chat_id)

