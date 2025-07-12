import json
import os
import logging
from typing import Dict, Any

# Create a logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Загружаем CHAT_URL из переменных окружения
CHAT_URL = os.getenv('CHAT_URL')

class MessageLoader:
    """Класс для загрузки и получения сообщений из JSON файла"""

    def __init__(self, messages_file: str = "messages.json"):
        self.messages_file = messages_file
        logger.debug(f"Initializing MessageLoader with messages file: {messages_file}")
        self._messages = self._load_messages()
        logger.debug(f"Loaded messages: {self._messages}")

    def _load_messages(self) -> Dict[str, Any]:
        """Загрузка сообщений из JSON файла"""
        try:
            # Получаем путь к корневой директории проекта
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            messages_path = os.path.join(project_root, self.messages_file)
            logger.debug(f"Attempting to load messages from: {messages_path}")

            if os.path.exists(messages_path):
                with open(messages_path, 'r', encoding='utf-8') as f:
                    loaded_messages = json.load(f)
                    logger.debug(f"Successfully loaded messages from {self.messages_file}")
                    return loaded_messages
            else:
                logger.error(f"Messages file not found: {self.messages_file}")
                return {}
        except Exception as e:
            logger.error(f"Error loading messages from {self.messages_file}: {e}")
            return {}

    def get_message(self, *keys: str, **kwargs) -> str:
        """
        Получает сообщение по ключам и форматирует его с переданными параметрами

        Args:
            *keys: Путь к сообщению в JSON (например, 'start_command', 'welcome_message')
            **kwargs: Параметры для форматирования строки

        Returns:
            Отформатированное сообщение
        """
        try:
            message = self._messages
            for key in keys:
                message = message[key]

            if isinstance(message, str) and kwargs:
                return message.format(**kwargs)
            return message
        except (KeyError, TypeError) as e:
            logger.error(f"Error finding message for keys {' -> '.join(keys)}. Error: {e}")
            logger.error(f"Available top-level keys in messages: {list(self._messages.keys())}")
            if keys and keys[0] in self._messages:
                logger.error(f"Sub-keys under {keys[0]}: {list(self._messages[keys[0]].keys())}")
            return f"Сообщение не найдено: {' -> '.join(keys)}"

    def get_button_text(self, section: str, button_key: str) -> str:
        """Получает текст кнопки"""
        return self.get_message(section, 'buttons', button_key)

    def reload_messages(self):
        """Перезагружает сообщения из файла"""
        self._messages = self._load_messages()

    def get_chat_url(self):
        """Получение URL чата из переменной окружения"""
        return CHAT_URL


# Создаем глобальный экземпляр для использования в проекте
messages = MessageLoader()
