import pathlib
import sys

# Ensure the repository root is on the import path so ``utils`` can be resolved
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from utils.message_chunker import send_long_message


class DummyBot:
    """Minimal bot stub that records messages and markups."""

    def __init__(self):
        self.messages = []
        self.markups = []

    def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):  # pragma: no cover - simple recorder
        self.messages.append(text)
        self.markups.append(reply_markup)


def test_send_long_message_splits_long_messages():
    """Large messages are paginated and reconstructed correctly."""

    long_text = "\n".join(f"Producto {i}" for i in range(1, 1200))  # simulate stock list
    bot = DummyBot()

    send_long_message(bot, 1, long_text)

    assert len(bot.messages) > 1  # should split into chunks
    assert bot.messages[0].startswith("1/")  # first chunk includes page header
    reconstructed = "".join(m.split("\n", 1)[1] if "\n" in m else m for m in bot.messages)
    assert reconstructed == long_text


def test_markup_only_on_first_chunk():
    """Reply markup must be attached only to the first message chunk."""

    text = "X" * 9000
    bot = DummyBot()
    markup = object()

    send_long_message(bot, 7, text, markup=markup)

    assert bot.markups[0] is markup
    assert all(m is None for m in bot.markups[1:])
    assert bot.messages[0].startswith("1/")
    assert bot.messages[-1].startswith(f"{len(bot.messages)}/")

