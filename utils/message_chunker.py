import math


def send_long_message(bot, chat_id, text, markup=None, parse_mode=None, **kwargs):
    """Send ``text`` split into 4096‑character chunks.

    Each chunk is prefixed with a simple ``"1/3"`` style header when the
    message spans multiple parts.  Any ``reply_markup`` is only attached to the
    first chunk.  Additional keyword arguments are forwarded to
    :meth:`bot.send_message` allowing callers to specify parameters such as
    ``disable_web_page_preview``.
    """
    if text is None:
        text = ""
    MAX = 4096
    # Determine number of chunks considering header size
    n = max(1, math.ceil(len(text) / MAX))
    while True:
        header_len = len(f"{n}/{n}\n") if n > 1 else 0
        chunk_size = MAX - header_len
        new_n = max(1, math.ceil(len(text) / chunk_size))
        if new_n == n:
            break
        n = new_n
    chunks = [text[i * chunk_size : (i + 1) * chunk_size] for i in range(n)]
    for idx, chunk in enumerate(chunks, 1):
        header = f"{idx}/{n}\n" if n > 1 else ""
        bot.send_message(
            chat_id,
            header + chunk,
            reply_markup=markup if idx == 1 else None,
            parse_mode=parse_mode,
            **kwargs,
        )
