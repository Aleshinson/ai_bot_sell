from abc import ABC, abstractmethod
from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.orm import Session
from database.models import Announcement
from database.db import get_session
from utils import messages
from typing import Optional, List


class BaseHandler(ABC):
    """Базовый класс для всех обработчиков"""

    def __init__(self):
        self.router = Router()
        self.setup_handlers()

    @abstractmethod
    def setup_handlers(self):
        """Настройка обработчиков для конкретного класса"""
        pass

    def get_db_session(self) -> Session:
        """Получение сессии базы данных"""
        return get_session()

    async def send_error_message(self, message_or_callback, error_key: str, **kwargs):
        """Отправка сообщения об ошибке"""
        error_text = messages.get_message('errors', error_key, **kwargs)

        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.answer(error_text)
        else:
            await message_or_callback.answer(error_text)

    async def check_permissions(self, user_id: int, moderator_ids: List[int]) -> bool:
        """Проверка прав модератора"""
        return user_id in moderator_ids

    def get_announcement_by_id(self, session: Session, announcement_id: int) -> Optional[Announcement]:
        """Получение объявления по ID"""
        return session.query(Announcement).filter_by(id=announcement_id).first()


class DatabaseMixin:
    """Миксин для работы с базой данных"""

    def safe_db_operation(self, operation_func, *args, **kwargs):
        """Безопасное выполнение операций с БД"""
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
        """Получение объявления по ID"""
        return session.query(Announcement).filter(Announcement.id == announcement_id).first()

    def create_announcement(self, session: Session, user_id: int, chat_id: int,
                                bot_name: str, bot_function: str, solution_description: str,
                                included_features: str, client_requirements: str,
                                launch_time: str, price: str, complexity: str) -> Announcement:
        """Создание нового объявления"""
        new_announcement = Announcement(
            user_id=user_id,
            chat_id=chat_id,
            bot_name=bot_name,
            bot_function=bot_function,
            solution_description=solution_description,
            included_features=included_features,
            client_requirements=client_requirements,
            launch_time=launch_time,
            price=price,
            complexity=complexity,
            is_approved=None
        )
        session.add(new_announcement)
        session.flush()  # Получаем ID без коммита
        return new_announcement

    def update_announcement_status(self, session: Session, announcement_id: int,
                                       is_approved: bool, moderator_id: int) -> Optional[Announcement]:
        """Обновление статуса объявления"""
        announcement = self.get_announcement_by_id(session, announcement_id)
        if announcement and announcement.is_approved is None:
            announcement.is_approved = is_approved
            announcement.moderator_id = moderator_id
            return announcement
        return None
