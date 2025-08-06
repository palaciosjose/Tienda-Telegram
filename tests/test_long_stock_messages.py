from utils.message_chunker import send_long_message


class DummyBot:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text, parse_mode=None, reply_markup=None):
        self.messages.append(text)


def test_send_long_message_splits_long_messages():
    long_text = 'X' * 9000
    bot = DummyBot()
    send_long_message(bot, 1, long_text)

    assert len(bot.messages) == 3
    assert bot.messages[0].startswith('1/3')
    reconstructed = ''.join(m.split('\n', 1)[1] if '\n' in m else m for m in bot.messages)
    assert reconstructed == long_text
