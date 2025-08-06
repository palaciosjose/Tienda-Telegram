class UnifiedNavigationSystem:
    """Provide navigation with breadcrumbs and quick actions.

    The system keeps track of the navigation *history* for every chat as a
    breadcrumb trail.  Additionally, quick actions are stored **per page** so
    that the last set of actions for each visited page can be retrieved later
    on.  This information is used by the tests to ensure a consistent user
    experience across the project.
    """

    def __init__(self):
        self._actions: dict[str, callable] = {}
        # ``_history`` maps ``chat_id`` to a list of visited pages in order.
        self._history: dict[int, list[str]] = {}
        # ``_quick_actions`` maps ``chat_id`` to a mapping of ``page`` -> actions.
        self._quick_actions: dict[int, dict[str, list[tuple[str, str]]]] = {}

    def register(self, name, func):
        self._actions[name] = func

    def handle(self, name, chat_id, store_id):
        action = self._actions.get(name)
        if action:
            action(chat_id, store_id)

    def create_universal_navigation(self, chat_id, page, quick_actions=None):
        """Create markup with provided quick actions plus home and cancel.

        Parameters
        ----------
        chat_id:
            Identifier of the chat for which the navigation is created.
        page:
            Name of the current page.  It is stored in the breadcrumb trail
            so that previous pages can be recovered if needed.
        quick_actions:
            Iterable with ``(text, callback_data)`` pairs that will be rendered
            before the standard home and cancel buttons.
        """

        if quick_actions is None:
            quick_actions = []

        # Track visited page and actions for history/quick access.
        self._history.setdefault(chat_id, []).append(page)
        self._quick_actions.setdefault(chat_id, {})[page] = list(quick_actions)

        import telebot

        markup = telebot.types.InlineKeyboardMarkup()
        for text, callback in quick_actions:
            markup.add(
                telebot.types.InlineKeyboardButton(text=text, callback_data=callback)
            )
        markup.add(
            telebot.types.InlineKeyboardButton(text='🏠 Inicio', callback_data='Volver al inicio'),
            telebot.types.InlineKeyboardButton(text='❌ Cancelar', callback_data='GLOBAL_CANCEL'),
        )
        return markup

    def get_quick_actions(self, chat_id, page=None):
        """Return quick actions for the last (or specified) page of a chat."""
        pages = self._history.get(chat_id, [])
        if page is None and pages:
            page = pages[-1]
        return self._quick_actions.get(chat_id, {}).get(page, [])

    def reset(self, chat_id):
        """Clear stored navigation data for ``chat_id``."""
        self._history.pop(chat_id, None)
        self._quick_actions.pop(chat_id, None)

nav_system = UnifiedNavigationSystem()
