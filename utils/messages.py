import json
import os
import logging
from typing import Dict, Any

# Create a logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MessageLoader:
    """Класс для загрузки и получения сообщений из JSON файла"""

    def __init__(self, messages_file: str = "messages.json"):
        self.messages_file = messages_file
        logger.debug(f"Initializing MessageLoader with messages file: {messages_file}")
        self._messages = self._load_messages()
        logger.debug(f"Loaded messages: {self._messages}")

    def _load_messages(self) -> Dict[str, Any]:
        """Загружает сообщения из JSON файла"""
        try:
            # Получаем путь к корневой директории проекта
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            messages_path = os.path.join(project_root, self.messages_file)
            logger.debug(f"Attempting to load messages from: {messages_path}")

            with open(messages_path, 'r', encoding='utf-8') as f:
                loaded_messages = json.load(f)
                logger.debug(f"Successfully loaded messages. Top-level keys: {list(loaded_messages.keys())}")
                if 'moderation' in loaded_messages:
                    logger.debug(f"Moderation keys: {list(loaded_messages['moderation'].keys())}")
                return loaded_messages
        except FileNotFoundError:
            logger.error(f"File {self.messages_file} not found! Check if the file exists in directory {messages_path}")
            print(f"Файл {self.messages_file} не найден! Проверьте наличие файла в директории {messages_path}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error reading JSON from file {messages_path}: file is damaged or incorrect.")
            print(f"Ошибка при чтении JSON из файла {messages_path}: файл поврежден или некорректен.")
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


# Создаем глобальный экземпляр для использования в проекте
messages = MessageLoader()
