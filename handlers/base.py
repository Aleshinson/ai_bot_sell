from abc import ABC, abstractmethod
from aiogram import Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.orm import Session
from database.models import Announcement
from database.db import get_session
from utils import messages
from typing import Optional, List


class BaseHandler(ABC):
    """Базовый класс для всех обработчиков."""

    def __init__(self):
        self.router = Router()
        self.setup_handlers()

    @abstractmethod
    def setup_handlers(self):
        """Настройка обработчиков для конкретного класса."""
        pass

    def get_db_session(self) -> Session:
        """
        Получение сессии базы данных.

        Returns:
            Session: Сессия базы данных.
        """
        return get_session()

    async def send_error_message(self, message_or_callback: Message | CallbackQuery, error_key: str, **kwargs):
        """
        Отправка сообщения об ошибке.

        Args:
            message_or_callback: Объект сообщения или обратного вызова.
            error_key: Ключ сообщения об ошибке.
            **kwargs: Дополнительные параметры для форматирования сообщения.
        """
        error_text = messages.get_message('errors', error_key, **kwargs)
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.answer(error_text, parse_mode='HTML')
        else:
            await message_or_callback.answer(error_text, parse_mode='HTML')

    async def check_permissions(self, user_id: int, moderator_ids: List[int]) -> bool:
        """
        Проверка прав модератора.

        Args:
            user_id: ID пользователя.
            moderator_ids: Список ID модераторов.

        Returns:
            bool: True, если пользователь является модератором, иначе False.
        """
        return user_id in moderator_ids

    def get_announcement_by_id(self, session: Session, announcement_id: int) -> Optional[Announcement]:
        """
        Получение объявления по ID.

        Args:
            session: Сессия базы данных.
            announcement_id: ID объявления.

        Returns:
            Optional[Announcement]: Объект объявления или None, если не найдено.
        """
        return session.query(Announcement).filter_by(id=announcement_id).first()


class DatabaseMixin:
    """Миксин для работы с базой данных."""

    def safe_db_operation(self, operation_func, *args, **kwargs):
        """
        Безопасное выполнение операций с базой данных.

        Args:
            operation_func: Функция для выполнения операции с БД.
            *args: Позиционные аргументы для функции.
            **kwargs: Именованные аргументы для функции.

        Returns:
            Результат выполнения функции или исключение в случае ошибки.
        """
        session = get_session()
        try:
            result = operation_func(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_announcement_by_id(self, session: Session, announcement_id: int) -> Optional[Announcement]:
        """
        Получение объявления по ID.

        Args:
            session: Сессия базы данных.
            announcement_id: ID объявления.

        Returns:
            Optional[Announcement]: Объект объявления или None, если не найдено.
        """
        return session.query(Announcement).filter(Announcement.id == announcement_id).first()

    def create_announcement(self, session: Session, user_id: int, chat_id: int,
                           bot_name: str, task_solution: str, included_features: str,
                           client_requirements: str, launch_time: str, price: str,
                           complexity: str, demo_url: str, documents: list, videos: list) -> Announcement:
        """
        Создание нового объявления.

        Args:
            session: Сессия базы данных.
            user_id: ID пользователя.
            chat_id: ID чата.
            bot_name: Название бота.
            task_solution: Описание задачи и решения.
            included_features: Включенные возможности.
            client_requirements: Требования к клиенту.
            launch_time: Срок запуска.
            price: Цена.
            complexity: Сложность.
            demo_url: Ссылка на демо.
            documents: Список документов.
            videos: Список видео.

        Returns:
            Announcement: Созданный объект объявления.
        """
        new_announcement = Announcement(
            user_id=user_id,
            chat_id=chat_id,
            bot_name=bot_name,
            task_solution=task_solution,
            included_features=included_features,
            client_requirements=client_requirements,
            launch_time=launch_time,
            price=price,
            complexity=complexity,
            demo_url=demo_url,
            documents=documents,
            videos=videos,
            is_approved=None
        )
        session.add(new_announcement)
        session.flush()
        return new_announcement

    def update_announcement_status(self, session: Session, announcement_id: int,
                                  is_approved: bool, moderator_id: int) -> Optional[Announcement]:
        """
        Обновление статуса объявления.

        Args:
            session: Сессия базы данных.
            announcement_id: ID объявления.
            is_approved: Статус одобрения.
            moderator_id: ID модератора.

        Returns:
            Optional[Announcement]: Обновленный объект объявления или None, если не найдено.
        """
        announcement = self.get_announcement_by_id(session, announcement_id)
        if announcement and announcement.is_approved is None:
            announcement.is_approved = is_approved
            announcement.moderator_id = moderator_id
            return announcement
        return None