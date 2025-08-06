class UnifiedNavigationSystem:
    """Provide navigation with breadcrumbs and quick actions."""

    def __init__(self):
        self._actions = {}
        self._history = {}
        self._quick_actions = {}

    def register(self, name, func):
        self._actions[name] = func

    def handle(self, name, chat_id, store_id):
        action = self._actions.get(name)
        if action:
            action(chat_id, store_id)

    def create_universal_navigation(self, chat_id, page, quick_actions=None):
        """Create markup with provided quick actions plus home and cancel."""
        if quick_actions is None:
            quick_actions = []
        self._history.setdefault(chat_id, []).append(page)
        self._quick_actions[chat_id] = quick_actions
        import telebot

        markup = telebot.types.InlineKeyboardMarkup()
        for text, callback in quick_actions:
            markup.add(telebot.types.InlineKeyboardButton(text=text, callback_data=callback))
        markup.add(
            telebot.types.InlineKeyboardButton(text='🏠 Inicio', callback_data='Volver al inicio'),
            telebot.types.InlineKeyboardButton(text='❌ Cancelar', callback_data='GLOBAL_CANCEL'),
        )
        return markup

    def get_quick_actions(self, chat_id):
        """Return quick actions last used for a chat."""
        return self._quick_actions.get(chat_id, [])

nav_system = UnifiedNavigationSystem()
