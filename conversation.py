import copy


class Conversation:
    SYSTEM_PROMPT = "Ты цифровой ассистент банка ZamanBank. Твоя цель помочь клиенту банка. Поздаровайся с пользователем, рассказав о функционале бота, затем отвечай на вопросы клиента как справочник: напрямую и полностью, без введения или заключения. Пытайся использовать functions если это уместно. Если не хватает данных для вызовы функции, спроси их у пользователя. При запросе данных у пользователя спрашивай по одному полю за раз и не предлагай контекстных действий."
    "При аналитике данных, давай персонализированные советы по оптимизации трат и увеличению сбережений."

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.history: list[dict[str, str]] = []
        self.is_new_conversation = True
        self._initialize_history()

    def _initialize_history(self):
        """Initialize conversation with system prompt."""
        self.add_developer_message(self.SYSTEM_PROMPT)

    def add_user_message(self, content: str):
        """Add a user message to the conversation history."""
        self.history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        """Add an assistant message to the conversation history."""
        self.history.append({"role": "assistant", "content": content})

    def add_developer_message(self, content: str):
        """Add a developer message to the conversation history."""
        self.history.append({"role": "developer", "content": content})

    def get_history_copy(self) -> list[dict]:
        """Return a deep copy of the conversation history."""
        return copy.deepcopy(self.history)

    def get_recent_history(self, n: int = 10) -> list[dict]:
        """Return a deep copy of the last n elements from conversation history."""
        return copy.deepcopy(self.history[-n:] if n > 0 else self.history)

    def mark_as_returning(self):
        """Mark conversation as no longer new."""
        self.is_new_conversation = False

    def should_greet(self) -> bool:
        """Check if this is a new conversation that needs greeting."""
        return self.is_new_conversation

    def get_serializable_history(self) -> list[dict]:
        """Return a JSON-serializable version of the history."""
        serializable = []
        for item in self.history:
            if isinstance(item, dict):
                # Only include simple dict items, not complex API response objects
                if all(
                    isinstance(v, (str, int, float, bool, type(None)))
                    for v in item.values()
                ):
                    serializable.append(item)
        return serializable
