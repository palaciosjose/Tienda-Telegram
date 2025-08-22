import shelve
from bot_instance import bot
import files
import dop
from navigation import nav_system
from utils.message_chunker import send_long_message


def _key(chat_id: int) -> str:
    return f"broadcast_{chat_id}"


def set_broadcast_content(chat_id: int, text: str, media: dict | None = None) -> None:
    """Store broadcast message content for ``chat_id``."""
    with shelve.open(files.sost_bd) as bd:
        state = bd.get(_key(chat_id), {"step": 1})
        state["text"] = text
        state["media"] = media
        bd[_key(chat_id)] = state


def set_broadcast_audience(chat_id: int, audience: str) -> None:
    """Store selected audience filter for ``chat_id``."""
    with shelve.open(files.sost_bd) as bd:
        state = bd.get(_key(chat_id), {"step": 2})
        state["audience"] = audience
        bd[_key(chat_id)] = state


def start_broadcast(store_id: int, chat_id: int) -> None:
    """Interactive wizard to create and send a broadcast."""
    key = _key(chat_id)
    with shelve.open(files.sost_bd) as bd:
        state = bd.get(key, {"step": 0, "store_id": store_id})
        state["store_id"] = store_id
        if state["step"] == 0:
            state["step"] = 1
            bd[key] = state
            markup = nav_system.create_universal_navigation(chat_id, "broadcast_content", store_id)
            send_long_message(
                bot,
                chat_id,
                "📣 Envía el mensaje para la difusión. Puedes adjuntar fotos, videos o documentos.",
                markup=markup,
            )
            return
        if state["step"] == 1:
            if not state.get("text") and not state.get("media"):
                markup = nav_system.create_universal_navigation(chat_id, "broadcast_content", store_id)
                send_long_message(bot, chat_id, "📣 Envía el mensaje para la difusión.", markup=markup)
                return
            state["step"] = 2
            bd[key] = state
        if state["step"] == 2:
            if not state.get("audience"):
                markup = nav_system.create_universal_navigation(chat_id, "broadcast_audience", store_id)
                send_long_message(
                    bot,
                    chat_id,
                    "👥 Indica la audiencia: 'all' para todos o 'buyers' para compradores.",
                    markup=markup,
                )
                return
            state["step"] = 3
            bd[key] = state
        if state["step"] == 3:
            markup = nav_system.create_universal_navigation(
                chat_id,
                "broadcast_ready",
                store_id,
                [("👁️ Vista previa", "broadcast_preview")],
            )
            send_long_message(bot, chat_id, "✅ Mensaje listo. Revisa la vista previa.", markup=markup)


def broadcast_preview(chat_id: int, store_id: int) -> None:
    """Show a preview of the broadcast message before sending."""
    key = _key(chat_id)
    with shelve.open(files.sost_bd) as bd:
        state = bd.get(key)
    if not state:
        markup = nav_system.create_universal_navigation(chat_id, "broadcast_preview", store_id)
        send_long_message(bot, chat_id, "❌ No hay mensaje para previsualizar.", markup=markup)
        return
    text = state.get("text", "")
    media = state.get("media")
    audience = state.get("audience", "all")
    if media:
        dop._send_media_message(chat_id, text, media)
    else:
        send_long_message(bot, chat_id, text)
    markup = nav_system.create_universal_navigation(
        chat_id,
        "broadcast_preview",
        store_id,
        [("✅ Confirmar", "broadcast_confirm")],
    )
    send_long_message(bot, chat_id, f"Audiencia: {audience}", markup=markup)


def broadcast_confirm(chat_id: int, store_id: int) -> None:
    """Send the broadcast to the selected audience."""
    key = _key(chat_id)
    with shelve.open(files.sost_bd) as bd:
        state = bd.get(key)
        if not state:
            markup = nav_system.create_universal_navigation(chat_id, "broadcast_confirm", store_id)
            send_long_message(bot, chat_id, "❌ No hay difusión pendiente.", markup=markup)
            return
        text = state.get("text", "")
        media = state.get("media")
        audience = state.get("audience", "all")
        bd.pop(key, None)
    result = dop.broadcast_message(audience, 1000000, text, media=media, shop_id=store_id)
    markup = nav_system.create_universal_navigation(chat_id, "broadcast_done", store_id)
    send_long_message(bot, chat_id, result, markup=markup)
    nav_system.reset(chat_id)


# Register callbacks with navigation system
nav_system.register("broadcast_preview", lambda chat_id, store_id: broadcast_preview(chat_id, store_id))
nav_system.register("broadcast_confirm", lambda chat_id, store_id: broadcast_confirm(chat_id, store_id))
