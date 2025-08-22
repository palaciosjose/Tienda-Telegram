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
        # ``_usage`` counts how many times each action was triggered per page.
        self._usage: dict[int, dict[str, dict[str, int]]] = {}

    def register(self, name, func):
        self._actions[name] = func

    def handle(self, name, chat_id, store_id):
        action = self._actions.get(name)
        if action:
            # Record usage for prioritisation purposes.  We assume the last
            # visited page is the one that triggered the action.
            page = self._history.get(chat_id, [])[-1:] or [None]
            if page[0] is not None:
                usage = self._usage.setdefault(chat_id, {}).setdefault(page[0], {})
                usage[name] = usage.get(name, 0) + 1
            action(chat_id, store_id)

    def create_universal_navigation(self, chat_id, page, store_id=None, quick_actions=None):
        """Create markup with provided quick actions plus home and cancel.

        Parameters
        ----------
        chat_id:
            Identifier of the chat for which the navigation is created.
        page:
            Name of the current page.  It is stored in the breadcrumb trail
            so that previous pages can be recovered if needed.
        store_id:
            Optional store identifier.  Kept for future use.  Older call sites
            may omit this argument, in which case the third positional argument
            is interpreted as ``quick_actions`` for backwards compatibility.
        quick_actions:
            Iterable with ``(text, callback_data)`` pairs that will be rendered
            before the standard home and cancel buttons.
        """

        if quick_actions is None and not isinstance(store_id, int):
            quick_actions = store_id
            store_id = None
        if quick_actions is None:
            quick_actions = []

        # Track visited page and actions for history/quick access.
        has_history = bool(self._history.get(chat_id))
        self._history.setdefault(chat_id, []).append(page)
        self._quick_actions.setdefault(chat_id, {})[page] = list(quick_actions)
        # Ensure usage counters exist only for current actions.
        page_usage = {
            callback: self._usage.get(chat_id, {})
            .get(page, {})
            .get(callback, 0)
            for _, callback in quick_actions
        }
        self._usage.setdefault(chat_id, {})[page] = page_usage

        import telebot

        markup = telebot.types.InlineKeyboardMarkup()

        # Render quick actions, packing at most three buttons per row for a
        # consistent layout across the bot.
        for i in range(0, len(quick_actions), 3):
            row = [
                telebot.types.InlineKeyboardButton(text=t, callback_data=c)
                for t, c in quick_actions[i : i + 3]
            ]
            markup.add(*row)

        # Standard navigation controls (back, refresh, home, cancel).  These
        # are also packed into rows of three to keep the keyboard compact.
        controls = []
        if has_history:
            controls.append(
                telebot.types.InlineKeyboardButton(
                    text='⬅️ Atrás', callback_data='GLOBAL_BACK'
                )
            )
        controls.append(
            telebot.types.InlineKeyboardButton(
                text='🔄 Actualizar', callback_data='GLOBAL_REFRESH'
            )
        )
        controls.append(
            telebot.types.InlineKeyboardButton(
                text='🏠 Inicio', callback_data='Volver al inicio'
            )
        )
        controls.append(
            telebot.types.InlineKeyboardButton(
                text='❌ Cancelar', callback_data='GLOBAL_CANCEL'
            )
        )

        for i in range(0, len(controls), 3):
            markup.add(*controls[i : i + 3])
        return markup

    def get_quick_actions(self, chat_id, page=None):
        """Return quick actions for the last (or specified) page of a chat."""
        pages = self._history.get(chat_id, [])
        if page is None and pages:
            page = pages[-1]
        actions = self._quick_actions.get(chat_id, {}).get(page, [])
        usage = self._usage.get(chat_id, {}).get(page, {})
        # Sort actions by usage count (descending).  ``sorted`` is stable so
        # equally used actions keep their original order.
        return sorted(actions, key=lambda a: usage.get(a[1], 0), reverse=True)

    def current(self, chat_id):
        """Return the current page for ``chat_id`` if available."""
        pages = self._history.get(chat_id, [])
        return pages[-1] if pages else None

    def back(self, chat_id):
        """Step back one level in the history for ``chat_id``."""
        pages = self._history.get(chat_id, [])
        if len(pages) >= 2:
            pages.pop()  # discard current page
            return pages[-1]
        return None

    def reset(self, chat_id):
        """Clear stored navigation data for ``chat_id``."""
        self._history.pop(chat_id, None)
        self._quick_actions.pop(chat_id, None)
        self._usage.pop(chat_id, None)

nav_system = UnifiedNavigationSystem()
