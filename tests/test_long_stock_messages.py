from tests.test_categories import setup_dop


class DummyBot:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text, parse_mode=None):
        self.messages.append(text)


def test_send_long_text_splits_long_messages(monkeypatch, tmp_path):
    dop = setup_dop(monkeypatch, tmp_path)
    long_text = 'X' * 9000
    bot = DummyBot()
    dop.send_long_text(bot, 1, long_text)

    assert len(bot.messages) > 1
    assert ''.join(bot.messages) == long_text
