import math


def send_long_message(bot, chat_id, text, markup=None, parse_mode=None):
    """Send text in chunks safe for Telegram (<4096 chars).

    Adds a simple page header ("1/3") when the text spans multiple messages.
    The reply markup, if provided, is only attached to the first message.
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
        )
